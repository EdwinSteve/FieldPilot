"""Build the demo farm the recorded two-day demo replays on (D074, D076).

The recorded answers (D076) cite observation ids such as `reading-1` and
the day's forecast, so the seeded rows must stay exactly these: clock paused
at 2 Nov 06:00 local (12 mm of rain forecast), plot 1, zone 1, one
soil-moisture sensor, reading 1 at 20.0, maize sown 1 Oct. The zone also has
air sensors with the 48 h before (D093): a dry day and a humid night, so the
crop-health specialist has a fungal risk to weigh. The simulator
learns the zone when the app starts, from that reading (§4.10), so no tick
is needed here.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from app.domain.enums import SensorKind
from app.domain.models import CropCycle, Plot, Reading, Sensor, SimClockState, Zone
from app.persistence.db import create_db_engine, init_schema
from app.persistence.unit_of_work import SqlUnitOfWork

START = datetime(2026, 11, 2, 11, 0, tzinfo=UTC)  # 2 Nov, 06:00 in Neiva (D076)
AIR_HOURS = 48
UTC_OFFSET_HOURS = -5
HUMID_NIGHT_LOCAL_HOURS = range(22, 30)  # 22:00 to 05:59, local: leaves stay wet


def air_at(at: datetime, humid_night: bool) -> tuple[float, float]:
    """Demo values (D038): temperature °C and relative humidity % at `at`."""
    hour = (at.hour + UTC_OFFSET_HOURS) % 24
    night = hour in HUMID_NIGHT_LOCAL_HOURS or hour + 24 in HUMID_NIGHT_LOCAL_HOURS
    if night:
        return (19.0, 94.0) if humid_night else (21.0, 82.0)
    afternoon = 12 <= hour <= 16
    return (30.0, 52.0) if afternoon else (25.0, 70.0)


@dataclass(frozen=True)
class SeedSummary:
    plot_id: int
    zone_id: int
    cycle_id: int


# The names the farmer reads, per language (D084). The recordings of each
# language name the zone as its seed does.
DEMO_NAMES = {
    "en": ("Demo farm, Neiva", "Zone 2"),
    "es": ("Finca demo, Neiva", "Zona 2"),
}


def seed_demo_farm(database_url: str, language: str = "en") -> SeedSummary:
    """Write the demo farm into a fresh database."""
    plot_name, zone_name = DEMO_NAMES[language]
    engine = create_db_engine(database_url)
    init_schema(engine)
    with SqlUnitOfWork(engine) as u:
        u.sim_clock.save(SimClockState(START, START, speed_factor=1.0, paused=True))
        plot = u.plots.add(
            Plot(
                plot_name,
                2.93,
                -75.28,
                2.0,
                START,
                utc_offset_hours=-5.0,
                municipality="Neiva",
                department="Huila",
            )
        )
        plot_id = _stored(plot.id, "plot")
        zone_id = _stored(
            u.zones.add(Zone(plot_id, zone_name, 0.5, 32.0, valve_id="v2")).id, "zone"
        )
        sensor = u.sensors.add(Sensor(zone_id, SensorKind.SOIL_MOISTURE, "%"))
        u.readings.add_many([Reading(_stored(sensor.id, "sensor"), 20.0, START)])
        _seed_air(u, zone_id)
        cycle_id = _stored(u.cycles.add(CropCycle(plot_id, "maize", date(2026, 10, 1))).id, "cycle")
        u.commit()
    engine.dispose()
    return SeedSummary(plot_id, zone_id, cycle_id)


def _seed_air(u: SqlUnitOfWork, zone_id: int) -> None:
    """Hourly air readings for the 48 h before START; only the last night is humid."""
    temperature = _stored(u.sensors.add(Sensor(zone_id, SensorKind.TEMPERATURE, "°C")).id, "sensor")
    humidity = _stored(u.sensors.add(Sensor(zone_id, SensorKind.HUMIDITY, "%")).id, "sensor")
    readings = []
    for hours_before in range(AIR_HOURS, 0, -1):
        at = START - timedelta(hours=hours_before)
        t, rh = air_at(at, humid_night=hours_before <= 12)
        readings += [Reading(temperature, t, at), Reading(humidity, rh, at)]
    u.readings.add_many(readings)


def _stored(entity_id: int | None, entity: str) -> int:
    if entity_id is None:
        raise RuntimeError(f"the database did not assign an id to the {entity}")
    return entity_id
