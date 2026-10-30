"""Build the demo farm the mock demo day replays on (D074).

The recorded answers cite day-one observation ids (`reading-1`, the 28 Oct
forecast), so the seeded rows must stay exactly these: clock paused at
28 Oct 06:00 local, plot 1, zone 1, one soil-moisture sensor, reading 1 at
20.0, maize sown 1 Oct, then one tick so the simulator learns the zone.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from app.domain.enums import SensorKind
from app.domain.models import CropCycle, Plot, Reading, Sensor, SimClockState, Zone
from app.main import create_app
from app.persistence.db import create_db_engine, init_schema
from app.persistence.unit_of_work import SqlUnitOfWork
from app.settings import Settings

START = datetime(2026, 10, 28, 11, 0, tzinfo=UTC)  # 06:00 in Neiva


@dataclass(frozen=True)
class SeedSummary:
    plot_id: int
    zone_id: int
    cycle_id: int


def seed_demo_farm(database_url: str) -> SeedSummary:
    """Write the demo farm into a fresh database file and tick once."""
    engine = create_db_engine(database_url)
    init_schema(engine)
    with SqlUnitOfWork(engine) as u:
        u.sim_clock.save(SimClockState(START, START, speed_factor=1.0, paused=True))
        plot = u.plots.add(
            Plot("Finca demo, Neiva", 2.93, -75.28, 2.0, START, utc_offset_hours=-5.0)
        )
        assert plot.id is not None
        zone = u.zones.add(Zone(plot.id, "Zona 2", 0.5, 32.0, valve_id="v2"))
        assert zone.id is not None
        sensor = u.sensors.add(Sensor(zone.id, SensorKind.SOIL_MOISTURE, "%"))
        assert sensor.id is not None
        u.readings.add_many([Reading(sensor.id, 20.0, START)])
        cycle = u.cycles.add(CropCycle(plot.id, "maize", date(2026, 10, 1)))
        assert cycle.id is not None
        u.commit()
    engine.dispose()
    create_app(Settings(database_url=database_url)).state.container.ticker.tick()
    assert plot.id is not None and zone.id is not None and cycle.id is not None
    return SeedSummary(plot.id, zone.id, cycle.id)
