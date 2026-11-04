"""The agronomist's tools: it leads the daily cycle (D093).

It consults the specialists in the same session, proposes the tasks that
cross domains through the gate, and withdraws its own tasks. It never
operates anything: a task runs only if the gate lets it, and fertilizer and
agrochemicals always wait for the farmer (D005).
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.agent.brief import BriefDraft, Observation, ObservationKind, ProposalSummary
from app.agent.citations import Fact, cited_facts, unsupported_numbers
from app.agent.field import ActionProposer, ActionRequest, Agronomy, TaskNotCancellableError
from app.agent.tools.agronomy import UNAVAILABLE
from app.agent.tools.field_tools import ReadContext
from app.agent.tools.orchestrator import Consultant
from app.agent.tools.registry import Tool, ToolRefusedError
from app.domain.models import JsonObject, JsonValue

PROPOSER = "agent:agronomist"
INPUTS = ("fertilizer", "agrochemical")  # need a product and a dose


class FocusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    focus: str = Field(
        default="", description="Optional: what you want the specialist to look at closely."
    )


class TaskInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: Literal["fertilizer", "agrochemical", "scouting_visit", "stress_alert"]
    zone_id: int | None = Field(description="The zone, or null for the whole plot.")
    scheduled_for: Literal["now"] | AwareDatetime = Field(
        description='"now", or an ISO 8601 time with offset, not in the past.'
    )
    product: str | None = Field(
        default=None, description="For fertilizer or agrochemical: what to apply, e.g. urea."
    )
    dose_kg_ha: float | None = Field(
        default=None, gt=0, description="For fertilizer or agrochemical: the dose in kg/ha."
    )
    rationale: str = Field(min_length=1, description="Why, for the farmer, in their language.")
    cited: list[str] = Field(min_length=1, description="observation_ids this task relies on")
    replaces_task_id: int | None = Field(
        default=None, description="To edit a task: the open task this one replaces."
    )


class CancelInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: int
    reason: str = Field(min_length=1, description="Why, for the farmer, in their language.")


class CloseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, description="What you decided today and why.")


def agronomist_tools(
    read: ReadContext,
    draft: BriefDraft,
    proposer: ActionProposer,
    consultant: Consultant,
    agronomy: Agronomy | None,
) -> list[Tool[Any]]:
    consults = [
        ("imaging", "Ask Imaging to read the satellite scene: vigor (NDVI) and bare soil."),
        ("crop_health", "Ask Crop health to assess disease, pest and stress risk per zone."),
        ("soil_nutrition", "Ask Soil nutrition to assess pH and N-P-K per zone."),
        ("irrigation", "Ask Irrigation to decide the water; it proposes through the gate. "
                       "Needs the monitoring assessment."),
        ("reporting", "Ask Reporting to write the farmer's report of the day. Consult it "
                      "last, after your own tasks, so the report includes them."),
    ]  # fmt: skip
    return [
        *(
            Tool(f"consult_{name}", text, FocusInput, _consult(name, read, draft, consultant))
            for name, text in consults
        ),
        Tool(
            "propose_task",
            "Propose a fertilizer, agrochemical, scouting visit or stress alert. The autonomy "
            "gate decides: fertilizer and agrochemicals always wait for the farmer. With "
            "replaces_task_id it edits an open task: the new one is proposed, then the old "
            "one is cancelled.",
            TaskInput,
            _propose(read, draft, proposer, agronomy),
            writes=True,
        ),
        Tool(
            "cancel_task",
            "Cancel an open task an agent proposed and that has not run, with the reason.",
            CancelInput,
            _cancel(read, draft, agronomy),
            writes=True,
        ),
        Tool(
            "close_day",
            "Close the day once Monitoring assessed the zones and Reporting saved the report.",
            CloseInput,
            _close(draft),
            closes_run=True,
        ),
    ]


def consult_task(subagent: str, plot_id: int, draft: BriefDraft, focus: str = "") -> str:
    """The task a specialist gets: the day, the brief so far, and the agronomist's focus."""
    day = draft.day.isoformat()
    brief = draft.freeze().to_json()
    ask = {
        "monitoring": f"Assess every zone of plot {plot_id} for {day}.",
        "imaging": f"Read the satellite imagery of plot {plot_id} for {day}.",
        "crop_health": f"Assess the crop health of every zone of plot {plot_id} for {day}.",
        "soil_nutrition": f"Assess the soil nutrition of every zone of plot {plot_id} for {day}.",
        "irrigation": f"Decide the irrigation of plot {plot_id} for {day}.",
        "reporting": f"Write the report of plot {plot_id} for {day}.",
    }[subagent]
    focus_text = f" The agronomist asks you to look at: {focus}" if focus.strip() else ""
    return f"{ask}{focus_text} Brief: {brief}"


def _finished(name: str, draft: BriefDraft) -> bool:
    """Whether the specialist left its result in the brief (irrigation may propose nothing)."""
    section: object = {
        "imaging": draft.imaging,
        "crop_health": draft.health,
        "soil_nutrition": draft.nutrition,
        "irrigation": True,
        "reporting": draft.report_id,
    }[name]
    return section is not None


def _consult(
    name: str, read: ReadContext, draft: BriefDraft, consultant: Consultant
) -> Callable[[FocusInput], JsonObject]:
    def handler(args: FocusInput) -> JsonObject:
        if name == "irrigation" and draft.assessment is None:
            raise ToolRefusedError("Irrigation needs the assessment: consult_monitoring first.")
        before = len(draft.proposals)
        run = consultant.consult(name, consult_task(name, read.plot_id, draft, args.focus))
        if str(run.status) != "completed" or not _finished(name, draft):
            raise ToolRefusedError(f"{name} did not finish ({run.status}). Go on without it.")
        output: JsonValue = run.output if isinstance(run.output, dict | str) else None
        result: dict[str, JsonValue] = {"status": str(run.status), "result": output}
        if name == "irrigation":
            result["proposals"] = [
                {"task_id": p.task_id, "action_type": p.action_type, "zone_id": p.zone_id,
                 "status": p.status, "outcome": p.outcome}
                for p in draft.proposals[before:]
            ]  # fmt: skip
        result["brief"] = draft.freeze().to_json()
        return result

    return handler


def _propose(
    read: ReadContext, draft: BriefDraft, proposer: ActionProposer, agronomy: Agronomy | None
) -> Callable[[TaskInput], JsonObject]:
    def handler(args: TaskInput) -> JsonObject:
        now = read.now()
        scheduled_for = now if args.scheduled_for == "now" else args.scheduled_for
        problems = _problems(read, draft, args, scheduled_for, now, agronomy)
        if problems:
            raise ToolRefusedError("Task refused before the gate: " + " ".join(problems))
        params: dict[str, float | str] = {}
        if args.product:
            params["product"] = args.product
        if args.dose_kg_ha is not None:
            params["dose_kg_ha"] = args.dose_kg_ha
        view = proposer.propose(
            ActionRequest(args.action_type, read.plot_id, args.zone_id, scheduled_for, params,
                          args.rationale, PROPOSER)
        )  # fmt: skip
        draft.proposals.append(
            ProposalSummary(view.task_id, args.action_type, args.zone_id, view.outcome,
                            view.effective_level, view.status)
        )  # fmt: skip
        observation_id = f"task-{view.task_id}"
        if args.dose_kg_ha is not None and read.ledger.get(observation_id) is None:
            read.ledger.add(Observation(observation_id, ObservationKind.TASK, args.zone_id,
                                        args.dose_kg_ha, "kg/ha", scheduled_for))  # fmt: skip
        result: dict[str, JsonValue] = {
            "task_id": view.task_id,
            "status": view.status,
            "outcome": view.outcome,
            "effective_level": view.effective_level,
            "reason": view.reason,
            "already_decided": view.already_decided,
        }
        if args.replaces_task_id is not None and agronomy is not None:
            reason = f"Replaced by task {view.task_id}."
            try:
                agronomy.cancel(read.plot_id, args.replaces_task_id, reason, PROPOSER)
            except TaskNotCancellableError as error:
                result["replaced"] = {"task_id": args.replaces_task_id, "error": str(error)}
            else:
                draft.cancelled.append(args.replaces_task_id)
                result["replaced"] = {"task_id": args.replaces_task_id, "status": "cancelled"}
        return result

    return handler


def _problems(
    read: ReadContext,
    draft: BriefDraft,
    args: TaskInput,
    scheduled_for: datetime,
    now: datetime,
    agronomy: Agronomy | None,
) -> list[str]:
    problems = []
    if agronomy is None:
        problems.append(UNAVAILABLE)
    if args.zone_id is not None and read.reader.zone(read.plot_id, args.zone_id) is None:
        problems.append(f"Zone {args.zone_id} is not in this plot.")
    if scheduled_for < now:
        problems.append(f"scheduled_for {scheduled_for.isoformat()} is in the past.")
    if args.action_type in INPUTS and (args.dose_kg_ha is None or not args.product):
        problems.append(f"{args.action_type} needs a product and dose_kg_ha.")
    if args.action_type not in INPUTS and (args.dose_kg_ha is not None or args.product):
        problems.append(f"{args.action_type} takes no product or dose.")
    if args.action_type == "fertilizer" and draft.nutrition is None:
        problems.append("A fertilizer needs the soil nutrition: consult_soil_nutrition first.")
    if args.action_type == "agrochemical" and draft.health is None:
        problems.append("An agrochemical needs the crop health: consult_crop_health first.")
    facts, missing = cited_facts(read.ledger, args.cited)
    if missing:
        problems.append(f"Cited ids you never read: {missing}.")
    own = [Fact(args.dose_kg_ha, "kg/ha")] if args.dose_kg_ha is not None else []
    unsupported = unsupported_numbers(args.rationale, facts + own)
    if unsupported:
        problems.append(f"Rationale numbers not in any cited observation: {unsupported}.")
    return problems


def _cancel(
    read: ReadContext, draft: BriefDraft, agronomy: Agronomy | None
) -> Callable[[CancelInput], JsonObject]:
    def handler(args: CancelInput) -> JsonObject:
        if agronomy is None:
            raise ToolRefusedError(UNAVAILABLE)
        try:
            task = agronomy.cancel(read.plot_id, args.task_id, args.reason, PROPOSER)
        except TaskNotCancellableError as error:
            raise ToolRefusedError(f"Cancel refused: {error}") from error
        draft.cancelled.append(task.task_id)
        return {"task_id": task.task_id, "status": task.status}

    return handler


def _close(draft: BriefDraft) -> Callable[[CloseInput], JsonObject]:
    def handler(args: CloseInput) -> JsonObject:
        problems = []
        if draft.assessment is None:
            problems.append("Monitoring has not assessed the zones: consult_monitoring.")
        if draft.report_id is None:
            problems.append("The farmer has no report yet: consult_reporting.")
        if problems:
            raise ToolRefusedError("The day cannot close: " + " ".join(problems))
        return {
            "closed": True,
            "summary": args.summary,
            "tasks_proposed": len(draft.proposals),
            "tasks_cancelled": len(draft.cancelled),
        }

    return handler
