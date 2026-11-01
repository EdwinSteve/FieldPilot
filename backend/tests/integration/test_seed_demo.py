"""The seeded farm is exactly what the recorded two-day demo replays on (D074, D076)."""

from datetime import UTC, date, datetime
from pathlib import Path

from app.domain.enums import SensorKind
from app.persistence.db import create_db_engine
from app.persistence.unit_of_work import SqlUnitOfWork
from app.services.demo_seed import START, seed_demo_farm

RAINY_MORNING = datetime(2026, 11, 2, 11, 0, tzinfo=UTC)  # 06:00 in Neiva, 12 mm forecast


def test_the_seed_writes_the_rows_the_recordings_cite(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'seed.db'}"

    summary = seed_demo_farm(url)

    assert (summary.plot_id, summary.zone_id, summary.cycle_id) == (1, 1, 1)
    with SqlUnitOfWork(create_db_engine(url)) as u:
        clock = u.sim_clock.get()
        [zone] = u.zones.list_by_plot(summary.plot_id)
        [sensor] = u.sensors.list_by_zone(zone.id or 0)
        reading = u.readings.latest(sensor.id or 0)
        cycle = u.cycles.get(summary.cycle_id)
    assert START == RAINY_MORNING
    assert clock is not None and (clock.sim_anchor, clock.paused) == (RAINY_MORNING, True)
    assert (zone.name, zone.field_capacity_pct) == ("Zona 2", 32.0)
    assert sensor.kind is SensorKind.SOIL_MOISTURE
    assert reading is not None and (reading.id, reading.value) == (1, 20.0)
    assert (cycle.crop, cycle.sowing_date) == ("maize", date(2026, 10, 1))
