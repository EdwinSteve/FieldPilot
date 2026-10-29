"""Startup reconciliation (D013, D014, D032).

Runs once in `create_app()`, after the configuration is validated and before
any request is served. It never executes anything again.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.actuation.ports import Actuator
from app.autonomy.messages import MessageCatalog, format_number
from app.domain.enums import EventKind, TaskStatus
from app.domain.models import Event, Notification
from app.persistence.ports import UnitOfWork
from app.safety.rules import IRRIGATION_ACTIONS
from app.services.execution import execution_event, task_id
from app.services.gate_context import volume_mm
from app.simulator.clock import Clock

UowFactory = Callable[[], UnitOfWork]
ACTOR = "system:reconciliation"
INTERRUPTED_KEY_PREFIX = "interrupted:"


@dataclass(frozen=True)
class ReconciliationReport:
    closed_as_executed: tuple[int, ...]  # actuator had a record: closed, not retried
    failed: tuple[int, ...]  # no record: FAILED, farmer notified, not retried
    interrupted: tuple[int, ...]  # running irrigation cut by the restart (D032)
    simulator_state_resumed: bool = False  # never: the simulator restarts empty (D014)


def reconcile_executions(
    uow: UowFactory, clock: Clock, actuator: Actuator, messages: MessageCatalog
) -> ReconciliationReport:
    now = clock.now()
    with uow() as u:
        logged = u.events.list()
        last_alive = logged[-1].occurred_at if logged else None
        open_requests = u.events.find_unclosed_execution_requests()
    closed: list[int] = []
    failed: list[int] = []
    for request in open_requests:
        if request.task_id is None or request.idempotency_key is None:
            continue
        result = actuator.lookup(request.idempotency_key)
        with uow() as u:
            if result is not None:
                u.tasks.transition(
                    request.task_id,
                    TaskStatus.EXECUTED,
                    execution_event(result, now, reconciled=True),
                )
                closed.append(request.task_id)
            else:
                _fail_unconfirmed(u, request.task_id, request.idempotency_key, now, messages)
                failed.append(request.task_id)
            u.commit()
    interrupted = (
        _report_interrupted(uow, actuator, messages, last_alive, now) if last_alive else []
    )
    return ReconciliationReport(tuple(closed), tuple(failed), tuple(interrupted))


def _fail_unconfirmed(
    u: UnitOfWork, stored_id: int, key: str, now: datetime, messages: MessageCatalog
) -> None:
    """D013: no record means not applied. Fail, notify, never retry."""
    u.tasks.transition(
        stored_id,
        TaskStatus.FAILED,
        Event(
            kind=EventKind.EXECUTION_FAILED,
            actor=ACTOR,
            reason="Execution requested before a restart and unknown to the actuator; "
            "not retried. A new decision is needed.",
            occurred_at=now,
            idempotency_key=key,
            inputs={"reconciled": True, "simulator_state_resumed": False},
        ),
    )
    message = messages.label("execution_not_confirmed", task_id=str(stored_id))
    u.notifications.add(Notification(message, now, task_id=stored_id))


def _report_interrupted(
    uow: UowFactory,
    actuator: Actuator,
    messages: MessageCatalog,
    last_alive: datetime,
    now: datetime,
) -> list[int]:
    """D032: an EXECUTED irrigation that may still have been running at the restart."""
    reported: list[int] = []
    with uow() as u:
        candidates = [
            (task, execution)
            for task in u.tasks.list(status=TaskStatus.EXECUTED)
            if task.action_type in IRRIGATION_ACTIONS
            for execution in u.events.list(task_id=task_id(task), kind=EventKind.EXECUTION)[-1:]
        ]
    for task, execution in candidates:
        key = execution.idempotency_key
        end = _natural_end(execution)
        if key is None or end is None or end <= last_alive or actuator.lookup(key) is not None:
            continue
        with uow() as u:
            if u.events.find_by_key(EventKind.NOTIFICATION, INTERRUPTED_KEY_PREFIX + key):
                continue  # already reported by an earlier restart
            if task.zone_id is not None:
                actuator.close_valve(task.zone_id, now)  # always allowed; real hardware may run
            requested = volume_mm(task)
            u.events.append(
                Event(
                    kind=EventKind.NOTIFICATION,
                    actor=ACTOR,
                    reason="Irrigation may have continued after the restart; the amount "
                    "applied is unknown (simulator state is not resumed).",
                    occurred_at=now,
                    task_id=task.id,
                    idempotency_key=INTERRUPTED_KEY_PREFIX + key,
                    inputs={
                        "requested_mm": requested,
                        "applied_mm": None,
                        "natural_end": end.isoformat(),
                        "last_event_before_restart": last_alive.isoformat(),
                        "simulator_state_resumed": False,
                    },
                )
            )
            message = messages.label(
                "irrigation_interrupted",
                requested_mm=format_number(requested),
                zone=str(task.zone_id),
            )
            u.notifications.add(Notification(message, now, task_id=task.id))
            u.commit()
        reported.append(task_id(task))
    return reported


def _natural_end(execution: Event) -> datetime | None:
    started = execution.inputs.get("started_at")
    target = execution.inputs.get("target_mm")
    rate = execution.inputs.get("rate_mm_per_h")
    if not isinstance(started, str) or not isinstance(target, int | float):
        return None
    if not isinstance(rate, int | float) or rate <= 0:
        return None
    return datetime.fromisoformat(started) + timedelta(hours=target / rate)
