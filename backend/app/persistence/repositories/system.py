"""Repositories for notifications and single-row system state."""

from collections.abc import Sequence
from datetime import datetime

from sqlmodel import Session, col, select

from app.domain.enums import EventKind
from app.domain.models import ControlState, Event, Notification, SimClockState
from app.persistence import mappers
from app.persistence.ports import EventRepository
from app.persistence.repositories._base import get_row_or_raise, insert
from app.persistence.tables import ControlStateRow, NotificationRow, SimClockStateRow

_SINGLETON_ID = 1


class SqlNotificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, notification: Notification) -> Notification:
        row = insert(self._session, mappers.notification_to_row(notification))
        return mappers.notification_from_row(row)

    def list(self, unread_only: bool = False) -> Sequence[Notification]:
        query = select(NotificationRow)
        if unread_only:
            query = query.where(col(NotificationRow.read_at).is_(None))
        query = query.order_by(col(NotificationRow.created_at).desc(), col(NotificationRow.id))
        return [mappers.notification_from_row(row) for row in self._session.exec(query)]

    def mark_read(self, notification_id: int, read_at: datetime) -> Notification:
        row = get_row_or_raise(self._session, NotificationRow, notification_id, "Notification")
        row.read_at = read_at
        self._session.flush()
        return mappers.notification_from_row(row)


class SqlControlStateRepository:
    """Emergency stop flag. Inactive until explicitly set; every change is logged."""

    def __init__(self, session: Session, events: EventRepository) -> None:
        self._session = session
        self._events = events

    def get(self) -> ControlState:
        row = self._session.get(ControlStateRow, _SINGLETON_ID)
        if row is None:
            return ControlState(emergency_stop_active=False)
        return mappers.control_state_from_row(row)

    def set_emergency_stop(self, active: bool, event: Event) -> ControlState:
        """Change the flag, writing `event` first in the same transaction."""
        if event.kind is not EventKind.EMERGENCY_STOP:
            raise ValueError("emergency stop changes need an emergency_stop event")
        self._events.append(event)
        row = self._session.get(ControlStateRow, _SINGLETON_ID) or ControlStateRow()
        row.emergency_stop_active = active
        row.changed_at = event.occurred_at
        row.changed_by = event.actor
        self._session.add(row)
        self._session.flush()
        return mappers.control_state_from_row(row)


class SqlSimClockStateRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self) -> SimClockState | None:
        row = self._session.get(SimClockStateRow, _SINGLETON_ID)
        return mappers.sim_clock_from_row(row) if row else None

    def save(self, state: SimClockState) -> SimClockState:
        row = self._session.get(SimClockStateRow, _SINGLETON_ID)
        if row is None:
            row = SimClockStateRow(
                sim_anchor=state.sim_anchor,
                wall_anchor=state.wall_anchor,
                speed_factor=state.speed_factor,
                paused=state.paused,
            )
            return mappers.sim_clock_from_row(insert(self._session, row))
        row.sim_anchor = state.sim_anchor
        row.wall_anchor = state.wall_anchor
        row.speed_factor = state.speed_factor
        row.paused = state.paused
        self._session.flush()
        return mappers.sim_clock_from_row(row)
