"""The one loop every subagent runs in (D044, D046, D048).

The model picks one tool per turn; the loop runs it through the registry and
sends the result back, until the subagent's closing tool succeeds, the turn
limit is reached, or the model service becomes unavailable.
"""

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.agent.llm.ports import LLMClient, LLMUnavailableError
from app.agent.messages import (
    AssistantText,
    LLMResponse,
    Message,
    ToolResult,
    UserMessage,
)
from app.agent.tools.registry import Tool, ToolRegistry
from app.agent.trace import TraceEntry, TraceSink
from app.domain.errors import ConfigError
from app.domain.models import JsonObject, JsonValue

MIN_TURNS = 2  # the nudge goes after turn max_turns - 1, so that turn must exist


class RunStatus(StrEnum):
    COMPLETED = "completed"
    TURN_LIMIT = "turn_limit"
    PAUSED = "paused"


@dataclass(frozen=True)
class Subagent:
    name: str
    system_prompt: str
    tool_names: frozenset[str]
    closing_tool: str | None  # None is valid here; the real catalogue always sets one (D053)
    may_write: bool = False  # only irrigation may hold writing tools (D054)
    prompt_sha256: str = ""  # of config/agents/<name>.md; set by the catalogue (D055)


@dataclass(frozen=True)
class AgentRun:
    run_id: str
    subagent: str
    status: RunStatus
    output: JsonObject | str | None
    transcript: tuple[Message, ...]
    turns: int  # completed model calls
    pauses: int = 0  # numbers the pause entries of the trace


@dataclass
class _Progress:
    """Mutable state of one run while the loop drives it."""

    run_id: str
    agent: Subagent
    transcript: list[Message]
    turns: int = 0
    pauses: int = 0
    output: JsonObject | str | None = field(default=None)

    def snapshot(self, status: RunStatus) -> AgentRun:
        return AgentRun(
            self.run_id,
            self.agent.name,
            status,
            self.output,
            tuple(self.transcript),
            self.turns,
            self.pauses,
        )


class AgentLoop:
    def __init__(
        self,
        llm: LLMClient,
        registry: ToolRegistry,
        trace: TraceSink,
        subagents: Sequence[Subagent],
        max_turns: int,
        timer: Callable[[], float] = time.perf_counter,
    ) -> None:
        if max_turns < MIN_TURNS:
            raise ConfigError(f"max_turns must be at least {MIN_TURNS}, got {max_turns}")
        self._llm = llm
        self._trace = trace
        self._max_turns = max_turns
        self._timer = timer
        self._subagents: dict[str, Subagent] = {}
        self._tools: dict[str, ToolRegistry] = {}
        for agent in subagents:
            if agent.name in self._subagents:
                raise ConfigError(f"subagent {agent.name!r} is defined twice")
            self._tools[agent.name] = validated_tools(agent, registry)
            self._subagents[agent.name] = agent

    def run(self, subagent: str, task: str, run_id: str) -> AgentRun:
        agent = self._subagents.get(subagent)
        if agent is None:
            raise ValueError(f"unknown subagent {subagent!r}")
        return self._drive(_Progress(run_id, agent, [UserMessage(task)]))

    def resume(self, run: AgentRun) -> AgentRun:
        """Continue a paused run from its transcript, in the same process (D046)."""
        if run.status is not RunStatus.PAUSED:
            raise ValueError(f"only a paused run can be resumed; this one is {run.status}")
        progress = _Progress(
            run.run_id,
            self._subagents[run.subagent],
            list(run.transcript),
            run.turns,
            run.pauses,
        )
        return self._drive(progress)

    def _drive(self, progress: _Progress) -> AgentRun:
        agent = progress.agent
        tools = self._tools[agent.name]
        while progress.turns < self._max_turns:
            turn = progress.turns + 1
            started = self._timer()
            try:
                response = self._llm.complete(
                    agent.system_prompt, tuple(progress.transcript), tools.specs()
                )
            except LLMUnavailableError as exc:
                # D048: nothing runs until resume(); the transcript is left as it was.
                progress.pauses += 1
                self._trace.record(
                    TraceEntry(
                        progress.run_id,
                        agent.name,
                        turn,
                        tool=None,
                        error=type(exc).__name__,
                        duration_ms=self._elapsed_ms(started),
                        pause=progress.pauses,
                        prompt_sha256=agent.prompt_sha256,
                    )
                )
                return progress.snapshot(RunStatus.PAUSED)
            progress.turns = turn
            if self._take_turn(progress, tools, response, started):
                return progress.snapshot(RunStatus.COMPLETED)
            if turn == self._max_turns - 1:
                progress.transcript.append(UserMessage(_nudge(agent)))
        progress.output = None
        return progress.snapshot(RunStatus.TURN_LIMIT)

    def _take_turn(
        self, progress: _Progress, tools: ToolRegistry, response: LLMResponse, started: float
    ) -> bool:
        """Apply one model response. True when it closed the run."""
        agent = progress.agent
        if response.text:
            progress.transcript.append(AssistantText(response.text))
        call = response.tool_call
        if call is None:
            text = response.text or ""
            self._record(progress, response, started, result={"text": text})
            if agent.closing_tool is None:
                progress.output = text
                return True
            progress.transcript.append(UserMessage(_reminder(agent.closing_tool)))
            return False
        progress.transcript.append(call)
        outcome = tools.call(call.name, call.arguments_json)
        progress.transcript.append(ToolResult(call.call_id, outcome.output_json()))
        self._record(
            progress,
            response,
            started,
            tool=call.name,
            arguments=outcome.arguments,
            result=outcome.result,
            error=outcome.error,
        )
        if outcome.closes_run:
            progress.output = outcome.result
            return True
        return False

    def _record(
        self,
        progress: _Progress,
        response: LLMResponse,
        started: float,
        *,
        tool: str | None = None,
        arguments: JsonValue = None,
        result: JsonObject | None = None,
        error: str | None = None,
    ) -> None:
        self._trace.record(
            TraceEntry(
                progress.run_id,
                progress.agent.name,
                progress.turns,
                tool,
                arguments,
                result,
                error,
                self._elapsed_ms(started),
                response.usage,
                prompt_sha256=progress.agent.prompt_sha256,
            )
        )

    def _elapsed_ms(self, started: float) -> int:
        return round((self._timer() - started) * 1000)


def validated_tools(agent: Subagent, registry: ToolRegistry) -> ToolRegistry:
    """The subagent's tools, or `ConfigError` (§4.8 rule 1, D054)."""
    if not agent.may_write:
        writing = sorted(name for name in agent.tool_names if _writes(registry.get(name)))
        if writing:
            raise ConfigError(
                f"subagent {agent.name!r} holds writing tools without may_write: {writing}"
            )
    tools = registry.subset(agent.tool_names, allow_writes=agent.may_write)
    closing = sorted(name for name in agent.tool_names if _closes(tools.get(name)))
    expected = [] if agent.closing_tool is None else [agent.closing_tool]
    if agent.closing_tool is not None and agent.closing_tool not in agent.tool_names:
        raise ConfigError(
            f"subagent {agent.name!r}: closing tool {agent.closing_tool!r} is not in its tools"
        )
    if closing != expected:
        raise ConfigError(
            f"subagent {agent.name!r}: closing tool is {agent.closing_tool!r}, "
            f"but the tools that close a run are {closing}"
        )
    return tools


def _closes(tool: Tool[Any] | None) -> bool:
    return tool is not None and tool.closes_run


def _writes(tool: Tool[Any] | None) -> bool:
    return tool is not None and tool.writes


def _reminder(closing_tool: str) -> str:
    return f"A text answer does not finish this task. Call {closing_tool} to finish."


def _nudge(agent: Subagent) -> str:
    if agent.closing_tool is None:
        return "This is your last turn. Answer now with what you have."
    return f"This is your last turn. Call {agent.closing_tool} now with what you have."
