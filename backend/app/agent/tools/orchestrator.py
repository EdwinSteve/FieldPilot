"""answer_farmer: the orchestrator's closing tool (D053). The same number check as reports."""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.agent.citations import cited_facts, unsupported_numbers
from app.agent.tools.field_tools import ReadContext
from app.agent.tools.registry import Tool, ToolRefusedError
from app.domain.models import JsonObject


class AnswerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text_es: str = Field(min_length=1, description="The answer to the farmer, in Spanish.")
    cited: list[str] = Field(description="observation_ids behind every number in the answer")


def orchestrator_tools(read: ReadContext) -> list[Tool[Any]]:
    return [
        Tool(
            "answer_farmer",
            "Answer the farmer. Closes the conversation turn. Every number with a unit must "
            "come from a cited observation.",
            AnswerInput,
            _answer(read),
            closes_run=True,
        )
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
