"""Use cases that connect the field simulator with persistence."""

from collections.abc import Callable, Collection, Sequence

from app.domain.enums import EventKind, SensorKind
from app.domain.models import Event, Reading
from app.persistence.ports import UnitOfWork
from app.simulator.clock import Clock
from app.simulator.field import FieldSimulator
from app.simulator.ports import SensorSource, ZoneSnapshot
from app.simulator.scenarios import Scenario

UowFactory = Callable[[], UnitOfWork]


def inject_scenario(
    simulator: FieldSimulator, scenario: Scenario, uow: UowFactory, clock: Clock, actor: str
) -> None:
    """Activate a scenario and log it."""
    simulator.inject(scenario)
    with uow() as u:
        u.events.append(
            Event(
                kind=EventKind.SCENARIO_INJECTED,
                actor=actor,
                reason=f"Scenario '{scenario.name}' injected into the simulator.",
                occurred_at=clock.now(),
                inputs=scenario.describe(),
            )
        )
        u.commit()


def record_readings(
    source: SensorSource,
    uow: UowFactory,
    clock: Clock,
    plot_id: int,
    zone_ids: Collection[int] | None = None,
) -> Sequence[Reading]:
    """Read the plot's zones (all, or only `zone_ids`) and store one reading per sensor,
    in one transaction."""
    at = clock.now()
    with uow() as u:
        readings: list[Reading] = []
        for zone in u.zones.list_by_plot(plot_id):
            if zone.id is None or (zone_ids is not None and zone.id not in zone_ids):
                continue
            snapshot = source.read(zone.id, at)
            readings.extend(
                Reading(sensor.id, _value_for(sensor.kind, snapshot), snapshot.at)
                for sensor in u.sensors.list_by_zone(zone.id)
                if sensor.id is not None
            )
        stored = u.readings.add_many(readings)
        u.commit()
    return stored


def _value_for(kind: SensorKind, snapshot: ZoneSnapshot) -> float:
    match kind:
        case SensorKind.SOIL_MOISTURE:
            return snapshot.soil_moisture_vwc
        case SensorKind.TEMPERATURE:
            return snapshot.temperature_c
        case SensorKind.HUMIDITY:
            return snapshot.relative_humidity_pct
