"""NOTIFY revert window and revert decisions (D007, D009, D011).

The deadline is stored on the task in simulated time and compared only with
the simulated clock, so a paused clock means a paused window.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import NoReturn

from app.actuation.ports import Actuator
from app.domain.enums import EventKind, TaskStatus
from app.domain.errors import DomainError
from app.domain.models import Event, Task, Zone
from app.persistence.ports import UnitOfWork
from app.safety.rules import IRRIGATION_ACTIONS
from app.services.execution import task_id
from app.services.gate_context import volume_mm
from app.simulator.clock import Clock

UowFactory = Callable[[], UnitOfWork]


class RevertRefusal(StrEnum):
    NOT_REVERTIBLE = "not_revertible"  # no window, or a final status
    WINDOW_CLOSED = "window_closed"
    ALREADY_APPLIED = "already_applied"  # irrigation ran to its target


class RevertRefusedError(DomainError):
    """Mapped to HTTP 409 in step 9. The refusal is already in the event log."""

    def __init__(self, reason: RevertRefusal, task_id: int) -> None:
        super().__init__(f"task {task_id} cannot be reverted: {reason}")
        self.reason = reason
        self.task_id = task_id


@dataclass(frozen=True)
class RevertWindow:
    deadline: datetime
    open: bool
    remaining: timedelta  # frozen while the simulated clock is paused (D011)


@dataclass(frozen=True)
class RevertResult:
    task: Task
    requested_mm: float
    applied_mm: float
    applied_liters: float


class RevertService:
    def __init__(self, uow: UowFactory, clock: Clock, actuator: Actuator) -> None:
        self._uow = uow
        self._clock = clock
        self._actuator = actuator

    def window(self, task: Task) -> RevertWindow | None:
        """The window as the backend sees it now. None: the task is not revertible."""
        if task.revert_deadline is None:
            return None
        now = self._clock.now()
        remaining = max(task.revert_deadline - now, timedelta(0))
        return RevertWindow(task.revert_deadline, now < task.revert_deadline, remaining)

    def revert(self, task_id: int, actor: str) -> RevertResult:
        """Cancel a scheduled task or stop a running irrigation, within the window."""
        now = self._clock.now()
        with self._uow() as u:
            task = u.tasks.get(task_id)
            zone = u.zones.get(task.zone_id) if task.zone_id is not None else None
            key = _execution_key(u, task_id) if task.status is TaskStatus.EXECUTED else None
        requested = volume_mm(task)
        refusal = _refusal(task, now)
        if refusal is not None:
            applied = requested if task.status is TaskStatus.EXECUTED else 0.0
            self._refuse(task, zone, actor, refusal, requested, applied, now)
        applied = 0.0
        if task.status is TaskStatus.EXECUTED:
            interrupted = self._actuator.interrupt(key, now) if key is not None else None
            if interrupted is None:
                self._refuse(
                    task, zone, actor, RevertRefusal.ALREADY_APPLIED, requested, requested, now
                )
            else:
                applied = interrupted
        with self._uow() as u:
            reverted = u.tasks.transition(
                task_id,
                TaskStatus.REVERTED,
                _revert_event(EventKind.REVERT, task, zone, actor, None, requested, applied, now),
            )
            u.commit()
        return RevertResult(reverted, requested, applied, _liters(applied, zone))

    def _refuse(
        self,
        task: Task,
        zone: Zone | None,
        actor: str,
        reason: RevertRefusal,
        requested: float,
        applied: float,
        now: datetime,
    ) -> NoReturn:
        """Log the refused attempt with its reason, change nothing, and raise (D007)."""
        with self._uow() as u:
            u.events.append(
                _revert_event(
                    EventKind.REVERT_REFUSED, task, zone, actor, reason, requested, applied, now
                )
            )
            u.commit()
        raise RevertRefusedError(reason, task_id(task))


def _refusal(task: Task, now: datetime) -> RevertRefusal | None:
    if task.revert_deadline is None:
        return RevertRefusal.NOT_REVERTIBLE
    if now >= task.revert_deadline:  # one second before is open; at the deadline, closed
        return RevertRefusal.WINDOW_CLOSED
    if task.status is TaskStatus.SCHEDULED:
        return None
    if task.status is TaskStatus.EXECUTED and task.action_type in IRRIGATION_ACTIONS:
        return None
    return RevertRefusal.NOT_REVERTIBLE


def _execution_key(u: UnitOfWork, task_id: int) -> str | None:
    executions = u.events.list(task_id=task_id, kind=EventKind.EXECUTION)
    return executions[-1].idempotency_key if executions else None


def _liters(applied_mm: float, zone: Zone | None) -> float:
    """1 mm over 1 m2 is 1 litre (D007)."""
    return applied_mm * zone.area_m2 if zone is not None else 0.0


def _revert_event(
    kind: EventKind,
    task: Task,
    zone: Zone | None,
    actor: str,
    refusal: RevertRefusal | None,
    requested: float,
    applied: float,
    now: datetime,
) -> Event:
    if refusal is None:
        reason = f"{task.action_type} reverted from {task.status}; {applied:g} mm applied."
    else:
        reason = f"Revert of {task.action_type} refused: {refusal}."
    return Event(
        kind=kind,
        actor=actor,
        reason=reason,
        occurred_at=now,
        task_id=task.id,
        autonomy_level=task.effective_level,
        rule=refusal,
        inputs={
            "status_before": task.status,
            "revert_deadline": task.revert_deadline.isoformat() if task.revert_deadline else None,
            "requested_mm": requested,
            "applied_mm": applied,
            "applied_liters": _liters(applied, zone),
        },
    )
