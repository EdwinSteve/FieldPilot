"""Append-only event log repository."""

from collections.abc import Sequence

from sqlmodel import Session, col, select

from app.domain.enums import EXECUTION_CLOSING_KINDS, EventKind
from app.domain.models import Event
from app.persistence import mappers
from app.persistence.repositories._base import insert
from app.persistence.tables import EventRow


class SqlEventRepository:
    """Event log. Rows are only ever inserted; there is no update or delete."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def append(self, event: Event) -> Event:
        """Insert an event. Fails if it reuses a (kind, idempotency_key) pair."""
        if event.id is not None:
            raise ValueError("events are append-only; this one is already stored")
        if event.kind is EventKind.EXECUTION_REQUESTED and not event.idempotency_key:
            raise ValueError("execution_requested events need an idempotency key")
        return mappers.event_from_row(insert(self._session, mappers.event_to_row(event)))

    def list(self, task_id: int | None = None, kind: EventKind | None = None) -> Sequence[Event]:
        query = select(EventRow)
        if task_id is not None:
            query = query.where(EventRow.task_id == task_id)
        if kind is not None:
            query = query.where(EventRow.kind == kind)
        query = query.order_by(col(EventRow.occurred_at), col(EventRow.id))
        return [mappers.event_from_row(row) for row in self._session.exec(query)]

    def find_by_key(self, kind: EventKind, idempotency_key: str) -> Event | None:
        """The event of `kind` with this key, if any; (kind, key) is unique."""
        query = select(EventRow).where(
            EventRow.kind == kind, EventRow.idempotency_key == idempotency_key
        )
        row = self._session.exec(query).first()
        return mappers.event_from_row(row) if row else None

    def find_unclosed_execution_requests(self) -> Sequence[Event]:
        """Execution requests whose idempotency key has no closing event.

        These are actions that may or may not have reached the actuator before
        a crash. Reconciliation decides what to do by key (D013).
        """
        closed_keys = select(EventRow.idempotency_key).where(
            col(EventRow.kind).in_(EXECUTION_CLOSING_KINDS),
            col(EventRow.idempotency_key).is_not(None),
        )
        query = (
            select(EventRow)
            .where(
                EventRow.kind == EventKind.EXECUTION_REQUESTED,
                col(EventRow.idempotency_key).not_in(closed_keys),
            )
            .order_by(col(EventRow.occurred_at), col(EventRow.id))
        )
        return [mappers.event_from_row(row) for row in self._session.exec(query)]
