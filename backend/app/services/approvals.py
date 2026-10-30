"""The farmer's decision on a task held for approval (D008, D062)."""

from collections.abc import Callable

from app.actuation.simulated import SUPPORTED_ACTIONS
from app.domain.enums import AutonomyLevel, EventKind, TaskStatus
from app.domain.errors import MissingDataError
from app.domain.models import Event, JsonValue, Task
from app.persistence.ports import UnitOfWork
from app.services.due_tasks import DueTaskRunner
from app.services.gate_decisions import verdict_from_event
from app.simulator.clock import Clock

UowFactory = Callable[[], UnitOfWork]


class ApprovalService:
    def __init__(self, uow: UowFactory, clock: Clock, due: DueTaskRunner) -> None:
        self._uow = uow
        self._clock = clock
        self._due = due

    def approve(self, stored_id: int, actor: str) -> Task:
        """Schedule a held task under the farmer's approval; run it now if it is due.

        The approval covers the rule codes of the verdict the farmer saw, and
        nothing else (D062). A type with no actuator command stays scheduled
        as a manual task.
        """
        now = self._clock.now()
        with self._uow() as u:
            codes = _held_codes(u, stored_id)
            task = u.tasks.transition(
                stored_id,
                TaskStatus.SCHEDULED,
                Event(
                    kind=EventKind.APPROVAL,
                    actor=actor,
                    reason="Approved by the farmer.",
                    occurred_at=now,
                    autonomy_level=AutonomyLevel.APPROVAL,
                    inputs={"approved_codes": codes},
                ),
            )
            u.commit()
        if task.scheduled_for <= now and task.action_type in SUPPORTED_ACTIONS:
            return self._due.run_task(task, now)
        return task

    def reject(self, stored_id: int, actor: str, reason: str | None = None) -> Task:
        """The farmer's "no" is final and logged as clearly as a "yes" (D008)."""
        explanation = f"Rejected by the farmer: {reason}" if reason else "Rejected by the farmer."
        with self._uow() as u:
            task = u.tasks.transition(
                stored_id,
                TaskStatus.REJECTED,
                Event(
                    kind=EventKind.REJECTION,
                    actor=actor,
                    reason=explanation,
                    occurred_at=self._clock.now(),
                    inputs={"reason": reason},
                ),
            )
            u.commit()
        return task


def _held_codes(u: UnitOfWork, stored_id: int) -> list[JsonValue]:
    """The rule codes of the stored verdict that held the task, sorted."""
    verdicts = u.events.list(task_id=stored_id, kind=EventKind.GATE_VERDICT)
    if not verdicts:
        raise MissingDataError(f"task {stored_id} has no stored verdict to approve")
    held = {v.code for v in verdict_from_event(verdicts[-1]).violations}
    return [str(code) for code in sorted(held)]
