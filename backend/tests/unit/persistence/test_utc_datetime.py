from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.dialects import sqlite

from app.persistence.types import UTCDateTime

DIALECT = sqlite.dialect()
BOGOTA = timezone(timedelta(hours=-5))


def test_aware_value_is_stored_as_naive_utc() -> None:
    stored = UTCDateTime().process_bind_param(datetime(2026, 10, 27, 1, 0, tzinfo=BOGOTA), DIALECT)

    assert stored == datetime(2026, 10, 27, 6, 0)
    assert stored is not None and stored.tzinfo is None


def test_naive_value_is_rejected() -> None:
    with pytest.raises(ValueError, match="naive"):
        UTCDateTime().process_bind_param(datetime(2026, 10, 27, 6, 0), DIALECT)


def test_value_read_back_is_aware_utc() -> None:
    loaded = UTCDateTime().process_result_value(datetime(2026, 10, 27, 6, 0), DIALECT)

    assert loaded == datetime(2026, 10, 27, 6, 0, tzinfo=UTC)
    assert loaded is not None and loaded.tzinfo is UTC


def test_none_passes_through() -> None:
    assert UTCDateTime().process_bind_param(None, DIALECT) is None
    assert UTCDateTime().process_result_value(None, DIALECT) is None
