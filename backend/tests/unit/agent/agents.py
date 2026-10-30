"""Tools, subagents and scripted responses shared by the agent tests."""

import json

from pydantic import BaseModel, Field

from app.agent.llm.ports import LLMClient
from app.agent.loop import AgentLoop, Subagent
from app.agent.messages import LLMResponse, ToolCall
from app.agent.tools.registry import Tool, ToolRefusedError, ToolRegistry
from app.agent.trace import TraceSink
from app.domain.models import JsonObject
from tests.fakes import FakeTimer


class ZoneArgs(BaseModel):
    zone_id: int = Field(ge=1)


class AssessmentArgs(BaseModel):
    summary: str
    moisture_pct: float


class Calls:
    """Counts handler calls, so a test can prove a tool did or did not run."""

    def __init__(self) -> None:
        self.read_moisture = 0
        self.submitted = 0

    def read(self, args: ZoneArgs) -> JsonObject:
        self.read_moisture += 1
        return {"zone_id": args.zone_id, "moisture_pct": 21.0, "observation_id": "reading-7"}

    def submit(self, args: AssessmentArgs) -> JsonObject:
        if args.moisture_pct != 21.0:
            raise ToolRefusedError(f"moisture_pct {args.moisture_pct} matches no stored reading.")
        self.submitted += 1
        return {"accepted": True, "summary": args.summary}


def make_registry(calls: Calls) -> ToolRegistry:
    return ToolRegistry(
        [
            Tool("read_moisture", "Latest soil moisture of a zone.", ZoneArgs, calls.read),
            Tool(
                "submit_assessment",
                "Submit the zone assessment. Closes the run.",
                AssessmentArgs,
                calls.submit,
                closes_run=True,
            ),
        ]
    )


MONITORING = Subagent(
    "monitoring",
    "You assess soil moisture.",
    frozenset({"read_moisture", "submit_assessment"}),
    closing_tool="submit_assessment",
)
CHAT = Subagent("chat", "You answer the farmer.", frozenset({"read_moisture"}), closing_tool=None)


def make_loop(llm: LLMClient, calls: Calls, trace: TraceSink, max_turns: int = 6) -> AgentLoop:
    return AgentLoop(
        llm,
        make_registry(calls),
        trace,
        [MONITORING, CHAT],
        max_turns=max_turns,
        timer=FakeTimer(),
    )


def tool(name: str, call_id: str, **arguments: object) -> LLMResponse:
    return LLMResponse(None, ToolCall(call_id, name, json.dumps(arguments)))


def raw_tool(name: str, call_id: str, arguments_json: str) -> LLMResponse:
    return LLMResponse(None, ToolCall(call_id, name, arguments_json))


def text(answer: str) -> LLMResponse:
    return LLMResponse(answer, None)


READ = tool("read_moisture", "c1", zone_id=2)
SUBMIT = tool("submit_assessment", "c2", summary="Zone 2 is dry.", moisture_pct=21.0)
