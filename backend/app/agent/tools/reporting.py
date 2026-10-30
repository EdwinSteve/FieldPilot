"""submit_report: Reporting's closing tool (D050, D052).

The report is saved only when every number traces to a cited observation and
every declared task status is the stored one. The third refusal in a run
escalates to the farmer instead of looping; the check itself never gives way.
"""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.agent.citations import cited_facts, unsupported_numbers
from app.agent.field import FarmerOutbox
from app.agent.tools.field_tools import ReadContext
from app.agent.tools.registry import Tool, ToolRefusedError
from app.domain.models import JsonObject, JsonValue

MAX_REFUSALS = 3
ESCALATION_TEXT = "report.escalated_unverified"


class DeclaredAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: int
    status: str = Field(description="The task status as stored, e.g. executed or scheduled.")


class ReportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text_es: str = Field(min_length=1, description="The day's report for the farmer, in Spanish.")
    cited: list[str] = Field(description="observation_ids behind every number in the text")
    actions: list[DeclaredAction] = Field(description="Every task the text talks about.")


def reporting_tools(read: ReadContext, outbox: FarmerOutbox) -> list[Tool[Any]]:
    return [
        Tool(
            "submit_report",
            "Submit the day's report for the farmer. Closes the task. Every number with a unit "
            "must come from a cited observation; every task you mention goes in actions with "
            "its stored status.",
            ReportInput,
            _submit(read, outbox),
            closes_run=True,
        )
    ]


def _submit(read: ReadContext, outbox: FarmerOutbox) -> Callable[[ReportInput], JsonObject]:
    refusals = 0

    def handler(args: ReportInput) -> JsonObject:
        nonlocal refusals
        problems = report_problems(read, args)
        if not problems:
            report_id = outbox.save_report(read.plot_id, args.text_es)
            return {"saved": True, "report_id": report_id}
        refusals += 1
        if refusals >= MAX_REFUSALS:
            # D052: stop the loop, never the verification. Nothing is saved.
            outbox.notify(read.plot_id, ESCALATION_TEXT)
            issues: list[JsonValue] = list(problems)
            return {
                "escalated": True,
                "saved": False,
                "refusals": refusals,
                "problems": issues,
            }
        raise ToolRefusedError(
            f"Report refused ({refusals} of {MAX_REFUSALS}): " + " ".join(problems)
        )

    return handler


def report_problems(read: ReadContext, args: ReportInput) -> list[str]:
    facts, missing = cited_facts(read.ledger, args.cited)
    problems = []
    if missing:
        problems.append(f"Cited ids you never read: {missing}.")
    unsupported = unsupported_numbers(args.text_es, facts)
    if unsupported:
        problems.append(f"Numbers not in any cited observation: {unsupported}.")
    for action in args.actions:
        stored = read.reader.task_status(read.plot_id, action.task_id)
        if stored is None:
            problems.append(f"Task {action.task_id} does not exist in this plot.")
        elif stored != action.status:
            problems.append(f"Task {action.task_id} is {stored}, not {action.status} as declared.")
    return problems
