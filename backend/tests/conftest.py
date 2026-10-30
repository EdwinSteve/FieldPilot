"""Shared fixtures: an in-memory database and small builders for test data."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.domain.enums import ActionType, AutonomyLevel, EventKind, TaskStatus
from app.domain.models import CropCycle, Event, Plot, Task, Zone
from app.persistence.db import create_db_engine, init_schema
from app.persistence.unit_of_work import SqlUnitOfWork
from app.phenology.catalog import CropSpec, load_crop_catalog

T0 = datetime(2026, 10, 27, 6, 0, tzinfo=UTC)


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = create_db_engine("sqlite://")
    init_schema(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def uow(engine: Engine) -> Callable[[], SqlUnitOfWork]:
    """Factory for fresh units of work on the test database."""
    return lambda: SqlUnitOfWork(engine)


@dataclass(frozen=True)
class FieldIds:
    plot_id: int
    zone_id: int
    cycle_id: int


@pytest.fixture
def field(uow: Callable[[], SqlUnitOfWork]) -> FieldIds:
    """A stored plot with one zone and an active maize cycle."""
    with uow() as u:
        plot = u.plots.add(
            Plot("Demo farm", 2.93, -75.28, 2.0, created_at=T0, utc_offset_hours=-5.0)
        )
        assert plot.id is not None
        zone = u.zones.add(Zone(plot.id, "Zone 2", 0.5, 32.0, valve_id="valve-2"))
        cycle = u.cycles.add(CropCycle(plot.id, "maize", date(2026, 10, 1)))
        u.commit()
    assert zone.id is not None and cycle.id is not None
    return FieldIds(plot.id, zone.id, cycle.id)


def make_task(field: FieldIds, status: TaskStatus = TaskStatus.SCHEDULED) -> Task:
    return Task(
        cycle_id=field.cycle_id,
        zone_id=field.zone_id,
        action_type=ActionType.IRRIGATION,
        params={"volume_mm": 15},
        scheduled_for=T0,
        status=status,
        effective_level=AutonomyLevel.AUTONOMOUS,
        rationale="Soil moisture 21 % and no rain forecast.",
        created_at=T0,
        updated_at=T0,
    )


def make_event(
    kind: EventKind,
    *,
    at: datetime = T0,
    idempotency_key: str | None = None,
    task_id: int | None = None,
) -> Event:
    return Event(
        kind=kind,
        actor="system",
        reason=f"test {kind}",
        occurred_at=at,
        task_id=task_id,
        idempotency_key=idempotency_key,
    )


def later(minutes: int) -> datetime:
    return T0 + timedelta(minutes=minutes)


CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
CROPS_DIR = CONFIG_DIR / "crops"
OPEN_METEO_DIR = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "open_meteo"
SAFETY_MAX_MOISTURE_PCT_FC = 85.0


@pytest.fixture(scope="session")
def maize() -> CropSpec:
    """The real maize catalog shipped in config/crops."""
    return load_crop_catalog(CROPS_DIR, SAFETY_MAX_MOISTURE_PCT_FC)["maize"]
