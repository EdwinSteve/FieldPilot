"""propose_action and finish: Irrigation's tools (§4.8, D044, D054).

propose_action is the agent's only writing tool. It never reaches the
actuator: it asks the ActionProposer, which goes through ProposalService and
the gate (principle 1). The checks here only refuse what is malformed; the
gate decides everything else.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.agent.brief import BriefDraft, Observation, ObservationKind, ProposalSummary
from app.agent.citations import Fact, cited_facts, unsupported_numbers
from app.agent.field import ActionProposer, ActionRequest, ProposalView
from app.agent.tools.field_tools import ReadContext
from app.agent.tools.registry import Tool, ToolRefusedError
from app.domain.models import JsonObject

PROPOSER = "agent:irrigation"
WATER_ACTIONS = ("irrigation", "extra_irrigation")


class ProposeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: Literal["irrigation", "extra_irrigation", "stop_irrigation"]
    zone_id: int
    volume_mm: float | None = Field(
        gt=0, description="Water to apply. Required for irrigation; null for stop_irrigation."
    )
    scheduled_for: Literal["now"] | AwareDatetime = Field(
        description='"now", or an ISO 8601 time with offset, not in the past.'
    )
    rationale: str = Field(min_length=1, description="Why, in Spanish, for the farmer.")
    cited: list[str] = Field(min_length=1, description="observation_ids this proposal relies on")


class FinishInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)


def irrigation_tools(
    read: ReadContext, draft: BriefDraft, proposer: ActionProposer
) -> list[Tool[Any]]:
    return [
        Tool(
            "propose_action",
            "Propose one irrigation action. The autonomy gate decides whether it runs, "
            "waits for the farmer, or is refused; the result tells you which.",
            ProposeInput,
            _propose(read, draft, proposer),
            writes=True,
        ),
        Tool(
            "finish",
            "Finish once every zone that needs action has a proposal, or none is needed.",
            FinishInput,
            lambda args: {
                "finished": True,
                "summary": args.summary,
                "proposals": len(draft.proposals),
            },
            closes_run=True,
        ),
    ]


def _propose(
    read: ReadContext, draft: BriefDraft, proposer: ActionProposer
) -> Callable[[ProposeInput], JsonObject]:
    def handler(args: ProposeInput) -> JsonObject:
        now = read.now()
        scheduled_for = now if args.scheduled_for == "now" else args.scheduled_for
        problems = _problems(read, draft, args, scheduled_for, now)
        if problems:
            raise ToolRefusedError("Proposal refused before the gate: " + " ".join(problems))
        params = {} if args.volume_mm is None else {"volume_mm": args.volume_mm}
        view = proposer.propose(
            ActionRequest(
                args.action_type,
                read.plot_id,
                args.zone_id,
                scheduled_for,
                params,
                args.rationale,
                PROPOSER,
            )
        )
        _record(read, draft, args, view, scheduled_for)
        return _result(view)

    return handler


def _problems(
    read: ReadContext,
    draft: BriefDraft,
    args: ProposeInput,
    scheduled_for: datetime,
    now: datetime,
) -> list[str]:
    problems = []
    if draft.assessment is None:
        problems.append("There is no submitted assessment to act on.")
    if read.reader.zone(read.plot_id, args.zone_id) is None:
        problems.append(f"Zone {args.zone_id} is not in this plot.")
    if scheduled_for < now:
        problems.append(f"scheduled_for {scheduled_for.isoformat()} is in the past.")
    if args.action_type in WATER_ACTIONS and args.volume_mm is None:
        problems.append(f"{args.action_type} needs volume_mm.")
    if args.action_type == "stop_irrigation" and args.volume_mm is not None:
        problems.append("stop_irrigation takes no volume_mm.")
    facts, missing = cited_facts(read.ledger, args.cited)
    if missing:
        problems.append(f"Cited ids you never read: {missing}.")
    own = [Fact(args.volume_mm, "mm")] if args.volume_mm is not None else []
    unsupported = unsupported_numbers(args.rationale, facts + own)
    if unsupported:
        problems.append(f"Rationale numbers not in any cited observation: {unsupported}.")
    return problems


def _record(
    read: ReadContext,
    draft: BriefDraft,
    args: ProposeInput,
    view: ProposalView,
    scheduled_for: datetime,
) -> None:
    draft.proposals.append(
        ProposalSummary(
            view.task_id,
            args.action_type,
            args.zone_id,
            view.outcome,
            view.effective_level,
            view.status,
        )
    )
    # The task becomes citable for the report. A repeated proposal returns a task the
    # ledger may already hold, so it is never re-added; a stop has no volume to state.
    observation_id = f"task-{view.task_id}"
    if args.volume_mm is not None and read.ledger.get(observation_id) is None:
        read.ledger.add(
            Observation(
                observation_id,
                ObservationKind.IRRIGATION,
                args.zone_id,
                args.volume_mm,
                "mm",
                scheduled_for,
            )
        )


def _result(view: ProposalView) -> JsonObject:
    return {
        "task_id": view.task_id,
        "observation_id": f"task-{view.task_id}",
        "status": view.status,
        "outcome": view.outcome,
        "effective_level": view.effective_level,
        "reason_es": view.reason_es,
        "already_decided": view.already_decided,
    }
