"""Record gate verdicts in the event log, once per proposal key (D023)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.autonomy.gate import GateContext
from app.domain.enums import AutonomyLevel, EventKind, GateOutcome
from app.domain.models import Event, JsonValue
from app.domain.proposals import ProposedAction
from app.domain.verdicts import GateVerdict
from app.domain.violations import RuleCode, RuleViolation
from app.persistence.ports import UnitOfWork
from app.simulator.clock import Clock

UowFactory = Callable[[], UnitOfWork]
ACTOR = "system:autonomy_gate"


@dataclass(frozen=True)
class RecordedVerdict:
    verdict: GateVerdict
    already_decided_at: datetime | None  # set when this proposal was decided before


def record_verdict(
    uow: UowFactory,
    clock: Clock,
    action: ProposedAction,
    context: GateContext,
    verdict: GateVerdict,
) -> RecordedVerdict:
    """Write one `gate_verdict` event, or return the earlier verdict for the same key.

    The caller shows a reused verdict with the "Ya decidida el ..." label, so a
    repeated request never looks ignored.
    """
    with uow() as u:
        existing = u.events.find_by_key(EventKind.GATE_VERDICT, action.proposal_key)
        if existing is not None:
            return RecordedVerdict(_verdict_from(existing), existing.occurred_at)
        u.events.append(
            Event(
                kind=EventKind.GATE_VERDICT,
                actor=ACTOR,
                reason=_reason(action, verdict),
                occurred_at=clock.now(),
                autonomy_level=verdict.effective_level,
                rule=verdict.reason_code,
                idempotency_key=action.proposal_key,
                inputs={
                    "proposal": _proposal_json(action),
                    "context": _context_json(context),
                    "verdict": _verdict_json(verdict),
                },
            )
        )
        u.commit()
    return RecordedVerdict(verdict, already_decided_at=None)


def _reason(action: ProposedAction, verdict: GateVerdict) -> str:
    """English audit summary; farmer-facing Spanish comes from the message catalog."""
    if not verdict.violations:
        return f"{action.action_type} allowed at level {verdict.effective_level}."
    codes = ", ".join(v.code for v in verdict.violations)
    return (
        f"{action.action_type} requested at {verdict.requested_level}, "
        f"set to {verdict.effective_level} because of: {codes}."
    )


def _proposal_json(action: ProposedAction) -> dict[str, JsonValue]:
    return {
        "action_type": action.action_type,
        "plot_id": action.plot_id,
        "zone_id": action.zone_id,
        "scheduled_for": action.scheduled_for.isoformat(),
        "params": dict(action.params),
        "rationale": action.rationale,
        "proposed_by": action.proposed_by,
    }


def _context_json(context: GateContext) -> dict[str, JsonValue]:
    safety = context.safety
    last = safety.last_irrigation_at
    return {
        "emergency_stop_active": safety.emergency_stop_active,
        "irrigated_mm_on_day": safety.irrigated_mm_on_day,
        "last_irrigation_at": last.isoformat() if last else None,
        "soil_moisture_vwc": safety.soil_moisture_vwc,
        "field_capacity_vwc": safety.field_capacity_vwc,
        "rain_forecast_mm_24h": safety.rain_forecast_mm_24h,
        "stage_level": context.stage_level,
    }


def _verdict_json(verdict: GateVerdict) -> dict[str, JsonValue]:
    return {
        "outcome": verdict.outcome,
        "requested_level": verdict.requested_level,
        "effective_level": verdict.effective_level,
        "reason_code": verdict.reason_code,
        "violations": [{"code": v.code, "params": dict(v.params)} for v in verdict.violations],
    }


def _verdict_from(event: Event) -> GateVerdict:
    data = event.inputs["verdict"]
    if not isinstance(data, dict):
        raise ValueError(f"event {event.id} has no stored verdict")
    violations = data["violations"]
    if not isinstance(violations, list):
        raise ValueError(f"event {event.id} has malformed violations")
    return GateVerdict(
        outcome=GateOutcome(str(data["outcome"])),
        requested_level=AutonomyLevel(str(data["requested_level"])),
        effective_level=AutonomyLevel(str(data["effective_level"])),
        violations=tuple(_violation_from(item) for item in violations),
    )


def _violation_from(item: JsonValue) -> RuleViolation:
    params = item.get("params") if isinstance(item, dict) else None
    if not isinstance(item, dict) or not isinstance(params, dict):
        raise ValueError(f"malformed stored violation: {item!r}")
    return RuleViolation(
        RuleCode(str(item["code"])),
        {k: v for k, v in params.items() if isinstance(v, int | float | str)},
    )
