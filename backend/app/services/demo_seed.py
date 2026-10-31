"""Build the demo farm the mock demo day replays on (D074).

The recorded answers cite day-one observation ids (`reading-1`, the 28 Oct
forecast), so the seeded rows must stay exactly these: clock paused at
28 Oct 06:00 local, plot 1, zone 1, one soil-moisture sensor, reading 1 at
20.0, maize sown 1 Oct. The simulator learns the zone when the app starts,
from that reading (§4.10), so no tick is needed here.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from app.domain.enums import SensorKind
from app.domain.models import CropCycle, Plot, Reading, Sensor, SimClockState, Zone
from app.persistence.db import create_db_engine, init_schema
from app.persistence.unit_of_work import SqlUnitOfWork

START = datetime(2026, 10, 28, 11, 0, tzinfo=UTC)  # 06:00 in Neiva


@dataclass(frozen=True)
class SeedSummary:
    plot_id: int
    zone_id: int
    cycle_id: int


def seed_demo_farm(database_url: str) -> SeedSummary:
    """Write the demo farm into a fresh database."""
    engine = create_db_engine(database_url)
    init_schema(engine)
    with SqlUnitOfWork(engine) as u:
        u.sim_clock.save(SimClockState(START, START, speed_factor=1.0, paused=True))
        plot = u.plots.add(
            Plot("Finca demo, Neiva", 2.93, -75.28, 2.0, START, utc_offset_hours=-5.0)
        )
        plot_id = _stored(plot.id, "plot")
        zone_id = _stored(u.zones.add(Zone(plot_id, "Zona 2", 0.5, 32.0, valve_id="v2")).id, "zone")
        sensor = u.sensors.add(Sensor(zone_id, SensorKind.SOIL_MOISTURE, "%"))
        u.readings.add_many([Reading(_stored(sensor.id, "sensor"), 20.0, START)])
        cycle_id = _stored(u.cycles.add(CropCycle(plot_id, "maize", date(2026, 10, 1))).id, "cycle")
        u.commit()
    engine.dispose()
    return SeedSummary(plot_id, zone_id, cycle_id)


def _stored(entity_id: int | None, entity: str) -> int:
    if entity_id is None:
        raise RuntimeError(f"the database did not assign an id to the {entity}")
    return entity_id
