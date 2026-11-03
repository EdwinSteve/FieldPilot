"""What stage 2 recorded about a cycle, sealed into the lot at harvest (§4.14). Pure."""

from collections.abc import Sequence

from app.domain.enums import ActionType, EventKind, TaskStatus
from app.domain.models import CropCycle, Event, JsonValue, Task
from app.market.trace.chain import digest

_IRRIGATION = frozenset({ActionType.IRRIGATION, ActionType.EXTRA_IRRIGATION})
_INPUTS = frozenset({ActionType.FERTILIZER, ActionType.AGROCHEMICAL})
# Written at or after the harvest: never part of what the harvest seals.
_AFTER_HARVEST = frozenset({EventKind.HARVEST_CONFIRMED, EventKind.LOT_COMMISSIONED})


def source_events(cycle_id: int, tasks: Sequence[Task], events: Sequence[Event]) -> list[Event]:
    """The cycle's cycle_started event and every event of its tasks, oldest first."""
    task_ids = {t.id for t in tasks if t.id is not None}
    return [
        e
        for e in events
        if e.kind not in _AFTER_HARVEST
        and (
            (e.task_id is not None and e.task_id in task_ids)
            or (e.kind is EventKind.CYCLE_STARTED and e.inputs.get("cycle_id") == cycle_id)
        )
    ]


def source_digest(events: Sequence[Event]) -> str:
    """SHA-256 of the events' canonical JSON: any later edit of the log changes it."""
    return digest(
        [
            {
                "id": e.id,
                "kind": e.kind.value,
                "occurred_at": e.occurred_at.isoformat(),
                "actor": e.actor,
                "task_id": e.task_id,
                "reason": e.reason,
                "inputs": dict(e.inputs),
            }
            for e in events
        ]
    )


def cultivation(cycle: CropCycle, tasks: Sequence[Task]) -> dict[str, JsonValue]:
    """Water and inputs applied. A manual cycle has no measurements: they are not guessed."""
    if not cycle.automated:
        return {
            "automated": False,
            "data_source": "declared",
            "irrigation_mm_total": None,
            "irrigation_events": None,
            "inputs_applied": [],
        }
    executed = [t for t in tasks if t.status is TaskStatus.EXECUTED]
    irrigations = [t for t in executed if t.action_type in _IRRIGATION]
    inputs: list[JsonValue] = [
        {"type": t.action_type.value, "date": t.scheduled_for.date().isoformat()}
        for t in executed
        if t.action_type in _INPUTS
    ]
    total = sum(_volume_mm(t) for t in irrigations)
    return {
        "automated": True,
        "data_source": "measured",
        "irrigation_mm_total": round(total, 1),
        "irrigation_events": len(irrigations),
        "inputs_applied": inputs,
    }


def plan_record(cycle: CropCycle, known: bool) -> dict[str, JsonValue]:
    """What the planner said at sowing; `known` is false for cycles before D083."""
    plan = cycle.plan
    return {
        "known": known,
        "followed_recommendation": (not cycle.own_risk) if known else None,
        "own_risk": cycle.own_risk if known else None,
        "model": None if plan is None else plan.model,
        "rank": None if plan is None else plan.rank,
        "predicted_rel_yield_p50": None if plan is None else plan.rel_yield_p50,
        "predicted_p_success": None if plan is None else plan.p_success,
    }


def _volume_mm(task: Task) -> float:
    value = task.params.get("volume_mm")
    return float(value) if isinstance(value, int | float) else 0.0
