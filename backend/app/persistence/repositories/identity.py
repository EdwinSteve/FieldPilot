"""Repositories for identity: users, refresh sessions, the auth audit log and plot members."""

from collections.abc import Iterable, Sequence
from datetime import datetime

from sqlmodel import Session, col, select

from app.identity.models import AuthEvent, RefreshSession, User
from app.persistence import mappers
from app.persistence.repositories._base import get_row_or_raise, insert
from app.persistence.tables import AuthEventRow, PlotMemberRow, RefreshSessionRow, UserRow


class SqlUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, user: User) -> User:
        return mappers.user_from_row(insert(self._session, mappers.user_to_row(user)))

    def get(self, user_id: int) -> User:
        return mappers.user_from_row(get_row_or_raise(self._session, UserRow, user_id, "User"))

    def find_by_phone(self, phone_e164: str) -> User | None:
        row = self._session.exec(select(UserRow).where(UserRow.phone == phone_e164)).first()
        return None if row is None else mappers.user_from_row(row)

    def update(self, user: User) -> User:
        if user.id is None:
            raise ValueError("cannot update a user that was never stored")
        row = self._session.merge(mappers.user_to_row(user))
        self._session.flush()
        return mappers.user_from_row(row)


class SqlRefreshSessionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, refresh: RefreshSession) -> RefreshSession:
        row = insert(self._session, mappers.refresh_session_to_row(refresh))
        return mappers.refresh_session_from_row(row)

    def find_by_hash(self, token_hash: str) -> RefreshSession | None:
        query = select(RefreshSessionRow).where(RefreshSessionRow.token_hash == token_hash)
        row = self._session.exec(query).first()
        return None if row is None else mappers.refresh_session_from_row(row)

    def mark_used(self, session_id: int, at: datetime) -> None:
        row = get_row_or_raise(self._session, RefreshSessionRow, session_id, "RefreshSession")
        row.used_at = at
        self._session.add(row)
        self._session.flush()

    def revoke_family(self, family_id: str, at: datetime) -> None:
        query = select(RefreshSessionRow).where(RefreshSessionRow.family_id == family_id)
        self._revoke(self._session.exec(query), at)

    def revoke_user(self, user_id: int, at: datetime) -> None:
        query = select(RefreshSessionRow).where(RefreshSessionRow.user_id == user_id)
        self._revoke(self._session.exec(query), at)

    def _revoke(self, rows: Iterable[RefreshSessionRow], at: datetime) -> None:
        for row in rows:
            if row.revoked_at is None:
                row.revoked_at = at
                self._session.add(row)
        self._session.flush()


class SqlAuthEventRepository:
    """Append-only: there is deliberately no update or delete."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def append(self, event: AuthEvent) -> AuthEvent:
        return mappers.auth_event_from_row(insert(self._session, mappers.auth_event_to_row(event)))

    def list(self, user_id: int | None = None) -> Sequence[AuthEvent]:
        query = select(AuthEventRow).order_by(col(AuthEventRow.id))
        if user_id is not None:
            query = query.where(AuthEventRow.user_id == user_id)
        return [mappers.auth_event_from_row(row) for row in self._session.exec(query)]


class SqlPlotMemberRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, plot_id: int, user_id: int) -> None:
        """Idempotent: adding an existing member changes nothing."""
        if not self.is_member(plot_id, user_id):
            insert(self._session, PlotMemberRow(plot_id=plot_id, user_id=user_id))

    def is_member(self, plot_id: int, user_id: int) -> bool:
        query = select(PlotMemberRow).where(
            PlotMemberRow.plot_id == plot_id, PlotMemberRow.user_id == user_id
        )
        return self._session.exec(query).first() is not None
