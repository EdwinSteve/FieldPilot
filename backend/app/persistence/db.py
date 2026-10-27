"""Engine creation and schema initialisation."""

from typing import Any

from sqlalchemy import Engine, event
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

from app.persistence import tables  # noqa: F401  (registers tables on the metadata)


def create_db_engine(database_url: str) -> Engine:
    """Create a SQLite engine with foreign keys enforced.

    An in-memory URL shares one connection so every session sees the same data.
    """
    options: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
    if database_url in ("sqlite://", "sqlite:///:memory:"):
        options["poolclass"] = StaticPool
    engine = create_engine(database_url, **options)
    event.listen(engine, "connect", _enable_foreign_keys)
    return engine


def init_schema(engine: Engine) -> None:
    """Create every table that does not exist yet (D012: no migrations)."""
    SQLModel.metadata.create_all(engine)


def _enable_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
