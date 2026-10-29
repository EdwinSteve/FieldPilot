"""The guarantee: a task never changes state without its event, and vice versa."""

from collections.abc import Callable

import pytest

from app.domain.enums import EventKind, TaskStatus
from app.domain.errors import InvalidTransitionError, NotFoundError
from app.domain.models import Event
from app.persistence.repositories.tasks import SqlTaskRepository
from app.persistence.tables import TaskRow
from app.persistence.unit_of_work import SqlUnitOfWork
from tests.conftest import FieldIds, later, make_event, make_task

UowFactory = Callable[[], SqlUnitOfWork]


def _stored_task_id(uow: UowFactory, field: FieldIds) -> int:
    with uow() as u:
        task = u.tasks.add(make_task(field), make_event(EventKind.PROPOSAL))
        u.commit()
    assert task.id is not None
    return task.id


def test_add_stores_task_and_creation_event_together(uow: UowFactory, field: FieldIds) -> None:
    task_id = _stored_task_id(uow, field)

    with uow() as u:
        events = u.events.list(task_id=task_id)
        assert u.tasks.get(task_id).status is TaskStatus.SCHEDULED
    assert [e.kind for e in events] == [EventKind.PROPOSAL]


def test_transition_writes_event_and_status(uow: UowFactory, field: FieldIds) -> None:
    task_id = _stored_task_id(uow, field)

    with uow() as u:
        updated = u.tasks.transition(
            task_id, TaskStatus.EXECUTED, make_event(EventKind.EXECUTION, at=later(5))
        )
        u.commit()

    assert updated.status is TaskStatus.EXECUTED
    assert updated.updated_at == later(5)
    with uow() as u:
        kinds = [e.kind for e in u.events.list(task_id=task_id)]
    assert kinds == [EventKind.PROPOSAL, EventKind.EXECUTION]


def test_invalid_transition_writes_nothing(uow: UowFactory, field: FieldIds) -> None:
    task_id = _stored_task_id(uow, field)

    with uow() as u, pytest.raises(InvalidTransitionError):
        u.tasks.transition(task_id, TaskStatus.REJECTED, make_event(EventKind.REJECTION))

    with uow() as u:
        assert u.tasks.get(task_id).status is TaskStatus.SCHEDULED
        assert [e.kind for e in u.events.list(task_id=task_id)] == [EventKind.PROPOSAL]


def test_failure_after_event_before_status_leaves_no_orphan_event(
    uow: UowFactory, field: FieldIds, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_id = _stored_task_id(uow, field)

    def crash(self: SqlTaskRepository, row: TaskRow, target: TaskStatus, event: Event) -> None:
        raise RuntimeError("simulated crash between event and status write")

    monkeypatch.setattr(SqlTaskRepository, "_write_status", crash)

    with uow() as u, pytest.raises(RuntimeError, match="simulated crash"):
        u.tasks.transition(task_id, TaskStatus.EXECUTED, make_event(EventKind.EXECUTION))

    with uow() as u:
        assert u.tasks.get(task_id).status is TaskStatus.SCHEDULED
        assert u.events.list(kind=EventKind.EXECUTION) == []
        assert [e.kind for e in u.events.list(task_id=task_id)] == [EventKind.PROPOSAL]


def test_nothing_persists_without_commit(uow: UowFactory, field: FieldIds) -> None:
    task_id = _stored_task_id(uow, field)

    with uow() as u:
        u.tasks.transition(task_id, TaskStatus.EXECUTED, make_event(EventKind.EXECUTION))

    with uow() as u:
        assert u.tasks.get(task_id).status is TaskStatus.SCHEDULED
        assert u.events.list(kind=EventKind.EXECUTION) == []


def test_task_cannot_be_created_already_executed(uow: UowFactory, field: FieldIds) -> None:
    with uow() as u, pytest.raises(InvalidTransitionError):
        u.tasks.add(make_task(field, TaskStatus.EXECUTED), make_event(EventKind.PROPOSAL))

    with uow() as u:
        assert u.tasks.list() == []
        assert u.events.list() == []


def test_event_for_another_task_is_rejected(uow: UowFactory, field: FieldIds) -> None:
    task_id = _stored_task_id(uow, field)
    foreign_event = make_event(EventKind.EXECUTION, task_id=task_id + 99)

    with uow() as u, pytest.raises(ValueError, match="expected"):
        u.tasks.transition(task_id, TaskStatus.EXECUTED, foreign_event)


def test_transition_of_missing_task_raises_not_found(uow: UowFactory, field: FieldIds) -> None:
    with uow() as u, pytest.raises(NotFoundError):
        u.tasks.transition(999, TaskStatus.EXECUTED, make_event(EventKind.EXECUTION))
