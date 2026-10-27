"""Shared helpers for SQL repositories."""

from sqlmodel import Session, SQLModel

from app.domain.errors import NotFoundError


def get_row_or_raise[RowT: SQLModel](
    session: Session, row_type: type[RowT], row_id: int, entity: str
) -> RowT:
    """Load a row by primary key or raise `NotFoundError`."""
    row = session.get(row_type, row_id)
    if row is None:
        raise NotFoundError(entity, row_id)
    return row


def insert[RowT: SQLModel](session: Session, row: RowT) -> RowT:
    """Insert a row and flush so its generated id is available."""
    session.add(row)
    session.flush()
    session.refresh(row)
    return row
