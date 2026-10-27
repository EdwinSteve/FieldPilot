"""Repositories for tasks and gate decisions."""

from collections.abc import Sequence
from dataclasses import replace

from sqlmodel import Session, col, select

from app.domain.enums import TaskStatus
from app.domain.models import Decision, Event, Task
from app.domain.task_transitions import ensure_initial_status, ensure_transition_allowed
from app.persistence import mappers
from app.persistence.ports import EventRepository
from app.persistence.repositories._base import get_row_or_raise, insert
from app.persistence.tables import DecisionRow, TaskRow


class SqlTaskRepository:
    """Task storage where every state change is paired with its event.

    Both writes happen in the caller's unit of work, event first, so either
    both are committed or neither is.
    """

    def __init__(self, session: Session, events: EventRepository) -> None:
        self._session = session
        self._events = events

    def add(self, task: Task, event: Event) -> Task:
        """Store a new task together with the event that created it."""
        ensure_initial_status(task.status)
        _ensure_event_targets(event, None)
        row = insert(self._session, mappers.task_to_row(task))
        if row.id is None:
            raise RuntimeError("database did not assign a task id")
        self._events.append(replace(event, task_id=row.id))
        return mappers.task_from_row(row)

    def get(self, task_id: int) -> Task:
        return mappers.task_from_row(get_row_or_raise(self._session, TaskRow, task_id, "Task"))

    def list(self, status: TaskStatus | None = None, cycle_id: int | None = None) -> Sequence[Task]:
        query = select(TaskRow)
        if status is not None:
            query = query.where(TaskRow.status == status)
        if cycle_id is not None:
            query = query.where(TaskRow.cycle_id == cycle_id)
        query = query.order_by(col(TaskRow.scheduled_for), col(TaskRow.id))
        return [mappers.task_from_row(row) for row in self._session.exec(query)]

    def transition(self, task_id: int, target: TaskStatus, event: Event) -> Task:
        """Move a task to `target`, writing `event` first in the same transaction.

        Raises `InvalidTransitionError` before writing anything if the
        lifecycle does not allow the change.
        """
        row = get_row_or_raise(self._session, TaskRow, task_id, "Task")
        ensure_transition_allowed(TaskStatus(row.status), target)
        _ensure_event_targets(event, task_id)
        self._events.append(replace(event, task_id=task_id))
        self._write_status(row, target, event)
        return mappers.task_from_row(row)

    def _write_status(self, row: TaskRow, target: TaskStatus, event: Event) -> None:
        row.status = target
        row.updated_at = event.occurred_at
        self._session.flush()


class SqlDecisionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, decision: Decision) -> Decision:
        row = insert(self._session, mappers.decision_to_row(decision))
        return mappers.decision_from_row(row)

    def list_by_task(self, task_id: int) -> Sequence[Decision]:
        query = (
            select(DecisionRow).where(DecisionRow.task_id == task_id).order_by(col(DecisionRow.id))
        )
        return [mappers.decision_from_row(row) for row in self._session.exec(query)]


def _ensure_event_targets(event: Event, task_id: int | None) -> None:
    if event.task_id is not None and event.task_id != task_id:
        raise ValueError(f"event refers to task {event.task_id}, expected {task_id}")
