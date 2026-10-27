from collections.abc import Callable
from dataclasses import replace

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.enums import EventKind
from app.persistence.unit_of_work import SqlUnitOfWork
from tests.conftest import later, make_event

UowFactory = Callable[[], SqlUnitOfWork]
REQUESTED = EventKind.EXECUTION_REQUESTED


def test_events_are_listed_in_occurrence_order(uow: UowFactory) -> None:
    with uow() as u:
        u.events.append(make_event(EventKind.GATE_VERDICT, at=later(10)))
        u.events.append(make_event(EventKind.PROPOSAL, at=later(0)))
        u.commit()

    with uow() as u:
        kinds = [e.kind for e in u.events.list()]
    assert kinds == [EventKind.PROPOSAL, EventKind.GATE_VERDICT]


def test_stored_event_cannot_be_appended_again(uow: UowFactory) -> None:
    with uow() as u:
        stored = u.events.append(make_event(EventKind.PROPOSAL))
        with pytest.raises(ValueError, match="append-only"):
            u.events.append(stored)


def test_execution_request_requires_idempotency_key(uow: UowFactory) -> None:
    with uow() as u, pytest.raises(ValueError, match="idempotency key"):
        u.events.append(make_event(REQUESTED))


def test_same_idempotency_key_cannot_be_requested_twice(uow: UowFactory) -> None:
    with uow() as u:
        u.events.append(make_event(REQUESTED, idempotency_key="task-1:attempt-1"))
        with pytest.raises(IntegrityError):
            u.events.append(make_event(REQUESTED, idempotency_key="task-1:attempt-1"))


def test_unclosed_requests_are_found_by_idempotency_key(uow: UowFactory) -> None:
    with uow() as u:
        u.events.append(make_event(REQUESTED, idempotency_key="done"))
        u.events.append(make_event(EventKind.EXECUTION, idempotency_key="done", at=later(1)))
        u.events.append(make_event(REQUESTED, idempotency_key="failed"))
        u.events.append(make_event(EventKind.EXECUTION_FAILED, idempotency_key="failed"))
        u.events.append(make_event(REQUESTED, idempotency_key="crashed"))
        u.commit()

    with uow() as u:
        unclosed = u.events.find_unclosed_execution_requests()

    assert [e.idempotency_key for e in unclosed] == ["crashed"]


def test_closing_event_of_another_kind_does_not_close_a_request(uow: UowFactory) -> None:
    with uow() as u:
        u.events.append(make_event(REQUESTED, idempotency_key="k"))
        u.events.append(replace(make_event(EventKind.REVERT), idempotency_key="k"))
        u.commit()

    with uow() as u:
        assert [e.idempotency_key for e in u.events.find_unclosed_execution_requests()] == ["k"]
