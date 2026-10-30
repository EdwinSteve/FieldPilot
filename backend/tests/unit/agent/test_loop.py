import json
from collections.abc import Iterable

import pytest

from app.agent.llm.mock import MockLLMClient
from app.agent.llm.ports import FixtureExhaustedError, LLMUnavailableError
from app.agent.loop import AgentLoop, RunStatus, Subagent
from app.agent.messages import AssistantText, ToolCall, ToolResult, UserMessage
from app.agent.tools.registry import Tool, ToolRegistry
from app.domain.errors import ConfigError
from tests.fakes import FlakyLLM, RecordingTrace
from tests.unit.agent.agents import (
    CHAT,
    MONITORING,
    READ,
    SUBMIT,
    AssessmentArgs,
    Calls,
    ZoneArgs,
    make_loop,
    make_registry,
    raw_tool,
    text,
    tool,
)

NUDGE = "This is your last turn. Call submit_assessment now with what you have."
REMINDER = "A text answer does not finish this task. Call submit_assessment to finish."


@pytest.fixture
def calls() -> Calls:
    return Calls()


@pytest.fixture
def trace() -> RecordingTrace:
    return RecordingTrace()


def test_plan_act_observe_until_the_closing_tool(calls: Calls, trace: RecordingTrace) -> None:
    llm = MockLLMClient([READ, SUBMIT])

    run = make_loop(llm, calls, trace).run("monitoring", "Assess zone 2.", "r1")

    assert run.status is RunStatus.COMPLETED
    assert run.output == {"accepted": True, "summary": "Zone 2 is dry."}
    assert run.turns == 2
    assert [e.tool for e in trace.entries] == ["read_moisture", "submit_assessment"]
    # The second call saw the first tool's result: plan -> act -> observe.
    assert llm.requests[1].messages[-1] == ToolResult(
        "c1", json.dumps(calls.read(ZoneArgs(zone_id=2)))
    )
    assert llm.requests[0].instructions == MONITORING.system_prompt
    assert {spec.name for spec in llm.requests[0].tools} == MONITORING.tool_names


def test_an_invalid_argument_comes_back_as_an_error_the_model_corrects(
    calls: Calls, trace: RecordingTrace
) -> None:
    llm = MockLLMClient([tool("read_moisture", "c1", zone_id=0), READ, SUBMIT])

    run = make_loop(llm, calls, trace).run("monitoring", "Assess zone 2.", "r1")

    feedback = llm.requests[1].messages[-1]
    assert isinstance(feedback, ToolResult)
    error = json.loads(feedback.output_json)["error"]
    assert error.startswith("Invalid arguments: zone_id:")
    assert run.status is RunStatus.COMPLETED
    assert trace.entries[0].error == error
    assert calls.read_moisture == 1


def test_invalid_json_is_recorded_with_its_raw_text(calls: Calls, trace: RecordingTrace) -> None:
    llm = MockLLMClient([raw_tool("read_moisture", "c1", "{zone"), SUBMIT])

    make_loop(llm, calls, trace).run("monitoring", "Assess zone 2.", "r1")

    assert trace.entries[0].arguments == "{zone"
    assert trace.entries[0].error is not None


def test_a_refused_closing_call_does_not_end_the_run(calls: Calls, trace: RecordingTrace) -> None:
    wrong = tool("submit_assessment", "c1", summary="dry", moisture_pct=30.0)
    llm = MockLLMClient([wrong, SUBMIT])

    run = make_loop(llm, calls, trace).run("monitoring", "Assess zone 2.", "r1")

    assert run.status is RunStatus.COMPLETED
    assert run.turns == 2
    assert trace.entries[0].error == "moisture_pct 30.0 matches no stored reading."


def test_text_without_closing_consumes_a_turn_and_gets_a_reminder(
    calls: Calls, trace: RecordingTrace
) -> None:
    llm = MockLLMClient([text("Zone 2 looks dry."), SUBMIT])

    run = make_loop(llm, calls, trace).run("monitoring", "Assess zone 2.", "r1")

    assert run.turns == 2
    assert llm.requests[1].messages[-2:] == (
        AssistantText("Zone 2 looks dry."),
        UserMessage(REMINDER),
    )
    assert trace.entries[0].tool is None
    assert trace.entries[0].result == {"text": "Zone 2 looks dry."}


def test_a_subagent_without_closing_tool_ends_on_text(calls: Calls, trace: RecordingTrace) -> None:
    llm = MockLLMClient([READ, text("Zone 2 is at 21 %.")])

    run = make_loop(llm, calls, trace).run("chat", "How is zone 2?", "r1")

    assert run.status is RunStatus.COMPLETED
    assert run.output == "Zone 2 is at 21 %."


def test_the_nudge_is_read_on_the_last_turn_only(calls: Calls, trace: RecordingTrace) -> None:
    llm = MockLLMClient([READ, READ, READ, READ])

    run = make_loop(llm, calls, trace, max_turns=4).run("monitoring", "Assess.", "r1")

    assert run.status is RunStatus.TURN_LIMIT
    nudged = [UserMessage(NUDGE) in request.messages for request in llm.requests]
    assert nudged == [False, False, False, True]
    assert llm.requests[3].messages[-1] == UserMessage(NUDGE)


def test_text_on_the_last_two_turns_ends_at_the_turn_limit(
    calls: Calls, trace: RecordingTrace
) -> None:
    """Observation 2: reminder and nudge go together; no extra turn is granted."""
    llm = MockLLMClient([READ, text("Still thinking."), text("Done, I think."), SUBMIT])

    run = make_loop(llm, calls, trace, max_turns=3).run("monitoring", "Assess.", "r1")

    assert run.status is RunStatus.TURN_LIMIT
    assert run.output is None
    assert run.turns == 3
    assert len(llm.requests) == 3  # the fourth response is never asked for
    assert llm.requests[2].messages[-3:] == (
        AssistantText("Still thinking."),
        UserMessage(REMINDER),
        UserMessage(NUDGE),
    )
    assert calls.submitted == 0
    assert [e.turn for e in trace.entries] == [1, 2, 3]


def test_closing_on_the_last_turn_completes(calls: Calls, trace: RecordingTrace) -> None:
    llm = MockLLMClient([READ, text("Hmm."), SUBMIT])

    run = make_loop(llm, calls, trace, max_turns=3).run("monitoring", "Assess.", "r1")

    assert run.status is RunStatus.COMPLETED
    assert run.turns == 3


def test_an_unavailable_model_pauses_and_runs_no_tool(calls: Calls, trace: RecordingTrace) -> None:
    llm = FlakyLLM(MockLLMClient([READ, SUBMIT]), failing_attempts=[2])

    run = make_loop(llm, calls, trace).run("monitoring", "Assess.", "r1")

    assert run.status is RunStatus.PAUSED
    assert run.output is None
    assert run.turns == 1
    assert calls.read_moisture == 1 and calls.submitted == 0
    paused = trace.entries[-1]
    assert (paused.turn, paused.tool, paused.error, paused.pause) == (
        2,
        None,
        "LLMUnavailableError",
        1,
    )


def test_resume_continues_from_the_same_transcript(calls: Calls, trace: RecordingTrace) -> None:
    mock = MockLLMClient([READ, SUBMIT])
    loop = make_loop(FlakyLLM(mock, failing_attempts=[2]), calls, trace)
    paused = loop.run("monitoring", "Assess.", "r1")

    done = loop.resume(paused)

    assert done.status is RunStatus.COMPLETED
    assert done.turns == 2
    assert mock.requests[1].messages == paused.transcript
    assert calls.read_moisture == 1


def test_only_a_paused_run_can_be_resumed(calls: Calls, trace: RecordingTrace) -> None:
    loop = make_loop(MockLLMClient([READ, SUBMIT]), calls, trace)
    done = loop.run("monitoring", "Assess.", "r1")

    with pytest.raises(ValueError, match="only a paused run"):
        loop.resume(done)


def test_an_exhausted_fixture_propagates_instead_of_pausing(
    calls: Calls, trace: RecordingTrace
) -> None:
    """D049: a broken fixture fails the test; it is never a paused run."""
    loop = make_loop(MockLLMClient([READ]), calls, trace)

    with pytest.raises(FixtureExhaustedError):
        loop.run("monitoring", "Assess.", "r1")
    assert not issubclass(FixtureExhaustedError, LLMUnavailableError)
    assert all(entry.pause is None for entry in trace.entries)


def test_an_unknown_subagent_is_refused(calls: Calls, trace: RecordingTrace) -> None:
    with pytest.raises(ValueError, match="unknown subagent 'imaging'"):
        make_loop(MockLLMClient([]), calls, trace).run("imaging", "Look.", "r1")


def test_tool_calls_are_kept_in_the_transcript(calls: Calls, trace: RecordingTrace) -> None:
    run = make_loop(MockLLMClient([READ, SUBMIT]), calls, trace).run("monitoring", "A.", "r1")

    kinds = [type(message) for message in run.transcript]
    assert kinds == [UserMessage, ToolCall, ToolResult, ToolCall, ToolResult]


# Startup validation (§4.8 rule 1).


def _build(*subagents: Subagent, max_turns: int = 6) -> AgentLoop:
    return AgentLoop(
        MockLLMClient([]), make_registry(Calls()), RecordingTrace(), subagents, max_turns
    )


def test_a_closing_tool_outside_the_subagent_tools_is_refused() -> None:
    agent = Subagent("m", "", frozenset({"read_moisture"}), closing_tool="submit_assessment")

    with pytest.raises(ConfigError, match="is not in its tools"):
        _build(agent)


def test_a_closing_tool_without_closes_run_is_refused() -> None:
    agent = Subagent("m", "", frozenset({"read_moisture"}), closing_tool="read_moisture")

    with pytest.raises(ConfigError, match="tools that close a run are"):
        _build(agent)


def test_a_second_tool_that_closes_runs_is_refused() -> None:
    registry = make_registry(Calls())
    registry.register(
        Tool("finish", "Also closes.", AssessmentArgs, Calls().submit, closes_run=True)
    )
    agent = Subagent(
        "m", "", frozenset({"submit_assessment", "finish"}), closing_tool="submit_assessment"
    )

    with pytest.raises(ConfigError, match=r"\['finish', 'submit_assessment'\]"):
        AgentLoop(MockLLMClient([]), registry, RecordingTrace(), [agent], 6)


def test_a_text_subagent_cannot_hold_a_closing_tool() -> None:
    agent = Subagent("chat", "", frozenset({"submit_assessment"}), closing_tool=None)

    with pytest.raises(ConfigError, match="closing tool is None"):
        _build(agent)


def test_an_unregistered_tool_is_refused() -> None:
    agent = Subagent("m", "", frozenset({"open_valve"}), closing_tool=None)

    with pytest.raises(ConfigError, match="unknown tools: open_valve"):
        _build(agent)


def test_duplicate_subagent_names_are_refused() -> None:
    with pytest.raises(ConfigError, match="defined twice"):
        _build(CHAT, CHAT)


def test_fewer_than_two_turns_is_refused() -> None:
    with pytest.raises(ConfigError, match="at least 2"):
        _build(MONITORING, max_turns=1)


def test_valid_subagents_build() -> None:
    loop = _build(MONITORING, CHAT, max_turns=2)

    assert isinstance(loop, AgentLoop)


def _with_writer() -> ToolRegistry:
    calls = Calls()
    registry = make_registry(calls)
    registry.register(Tool("propose_action", "Writes.", ZoneArgs, calls.read, writes=True))
    return registry


def test_a_writing_tool_without_may_write_is_refused_at_startup() -> None:
    """D054, startup check: names the subagent and the tool."""
    agent = Subagent(
        "monitoring",
        "",
        frozenset({"propose_action", "submit_assessment"}),
        closing_tool="submit_assessment",
    )

    with pytest.raises(ConfigError, match=r"'monitoring' holds writing tools without may_write"):
        AgentLoop(MockLLMClient([]), _with_writer(), RecordingTrace(), [agent], 6)


def test_a_subagent_with_may_write_may_hold_a_writing_tool() -> None:
    agent = Subagent(
        "irrigation",
        "",
        frozenset({"propose_action", "submit_assessment"}),
        closing_tool="submit_assessment",
        may_write=True,
    )

    loop = AgentLoop(MockLLMClient([]), _with_writer(), RecordingTrace(), [agent], 6)

    assert isinstance(loop, AgentLoop)


class SpyRegistry(ToolRegistry):
    """Records the allow_writes each subset was asked with."""

    def __init__(self, base: ToolRegistry) -> None:
        super().__init__(tool for name in sorted(base.names()) if (tool := base.get(name)))
        self.allow_writes: dict[frozenset[str], bool] = {}

    def subset(self, names: Iterable[str], *, allow_writes: bool) -> ToolRegistry:
        wanted = frozenset(names)
        self.allow_writes[wanted] = allow_writes
        return super().subset(wanted, allow_writes=allow_writes)


def test_the_loop_asks_subset_for_writes_only_with_may_write() -> None:
    """D054: the runtime check gets the subagent's own permission, never a blanket True."""
    registry = SpyRegistry(_with_writer())
    irrigation = Subagent(
        "irrigation",
        "",
        frozenset({"propose_action", "submit_assessment"}),
        closing_tool="submit_assessment",
        may_write=True,
    )

    AgentLoop(MockLLMClient([]), registry, RecordingTrace(), [MONITORING, irrigation], 6)

    assert registry.allow_writes == {MONITORING.tool_names: False, irrigation.tool_names: True}
