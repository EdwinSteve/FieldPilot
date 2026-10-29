"""Custom column types."""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    """Store aware datetimes as naive UTC and return them as aware UTC.

    SQLite drops timezone information, so without this a value read back
    would be naive and comparisons against aware datetimes (e.g. the revert
    deadline) would fail or, worse, be off by the local offset. Naive input
    is rejected because its meaning is ambiguous.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(  # SQLAlchemy's signature
        self,
        value: datetime | None,
        dialect: Dialect,  # noqa: ARG002
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"naive datetime not allowed: {value!r}")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(  # SQLAlchemy's signature
        self,
        value: datetime | None,
        dialect: Dialect,  # noqa: ARG002
    ) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC)
