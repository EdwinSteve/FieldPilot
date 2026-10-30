"""The orchestrator's tools: consult_monitoring and answer_farmer (D044, D053, D057).

answer_farmer applies the same number check as reports. The chat is
read-only for now (D057): there is no consult_irrigation.
"""

from collections.abc import Callable
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.agent.brief import BriefDraft
from app.agent.citations import cited_facts, unsupported_numbers
from app.agent.loop import AgentRun
from app.agent.tools.field_tools import ReadContext
from app.agent.tools.registry import Tool, ToolRefusedError
from app.domain.models import JsonObject


class AnswerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text_es: str = Field(min_length=1, description="The answer to the farmer, in Spanish.")
    cited: list[str] = Field(description="observation_ids behind every number in the answer")


class Consultant(Protocol):
    """Runs a subagent inside the same session; bound once the loop exists."""

    def consult(self, subagent: str, task: str) -> AgentRun: ...


class QuestionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, description="What you need Monitoring to assess.")


def orchestrator_tools(
    read: ReadContext, draft: BriefDraft, consultant: Consultant
) -> list[Tool[Any]]:
    return [
        Tool(
            "consult_monitoring",
            "Ask the Monitoring subagent to assess every zone. Returns its verified "
            "assessment; the values it read become citable.",
            QuestionInput,
            _consult_monitoring(draft, consultant),
        ),
        Tool(
            "answer_farmer",
            "Answer the farmer. Closes the conversation turn. Every number with a unit must "
            "come from a cited observation.",
            AnswerInput,
            _answer(read),
            closes_run=True,
        ),
    ]


def _answer(read: ReadContext) -> Callable[[AnswerInput], JsonObject]:
    def handler(args: AnswerInput) -> JsonObject:
        facts, missing = cited_facts(read.ledger, args.cited)
        problems = [f"Cited ids you never read: {missing}."] if missing else []
        unsupported = unsupported_numbers(args.text_es, facts)
        if unsupported:
            problems.append(f"Numbers not in any cited observation: {unsupported}.")
        if problems:
            raise ToolRefusedError("Answer refused: " + " ".join(problems))
        return {"answer": args.text_es}

    return handler


def _consult_monitoring(
    draft: BriefDraft, consultant: Consultant
) -> Callable[[QuestionInput], JsonObject]:
    def handler(args: QuestionInput) -> JsonObject:
        run = consultant.consult("monitoring", args.question)
        if draft.assessment is None:
            raise ToolRefusedError(f"Monitoring did not finish its assessment ({run.status}).")
        brief = draft.freeze().to_json()
        return {"status": str(run.status), "brief": brief}

    return handler
