from collections.abc import Callable
from datetime import timedelta

from app.domain.enums import EventKind, SensorKind
from app.domain.models import Sensor
from app.persistence.unit_of_work import SqlUnitOfWork
from app.services.simulation import inject_scenario, record_readings
from app.simulator.clock import SimClock
from app.simulator.field import FieldSimulator
from app.simulator.scenarios import DroughtScenario
from app.simulator.water_balance import SoilParams
from tests.conftest import T0, FieldIds
from tests.fakes import FakeWall

UowFactory = Callable[[], SqlUnitOfWork]


def paused_clock_at(minutes: int) -> SimClock:
    return SimClock.start(T0 + timedelta(minutes=minutes), FakeWall(T0), paused=True)


def test_record_readings_stores_one_value_per_sensor(uow: UowFactory, field: FieldIds) -> None:
    with uow() as u:
        for kind, unit in [
            (SensorKind.SOIL_MOISTURE, "%"),
            (SensorKind.TEMPERATURE, "C"),
            (SensorKind.HUMIDITY, "%"),
        ]:
            u.sensors.add(Sensor(field.zone_id, kind, unit))
        u.commit()
    sim = FieldSimulator(T0, seed=3)
    sim.add_zone(field.zone_id, SoilParams(), initial_vwc=25.0)
    clock = paused_clock_at(60)

    stored = record_readings(sim, uow, clock, field.plot_id)

    snapshot = sim.read(field.zone_id, clock.now())
    assert sorted(r.value for r in stored) == sorted(
        [snapshot.soil_moisture_vwc, snapshot.temperature_c, snapshot.relative_humidity_pct]
    )
    assert {r.recorded_at for r in stored} == {snapshot.at}


def test_inject_scenario_logs_its_parameters(uow: UowFactory) -> None:
    sim = FieldSimulator(T0)
    clock = paused_clock_at(0)
    drought = DroughtScenario(start=T0, end=T0 + timedelta(days=2))

    inject_scenario(sim, drought, uow, clock, actor="demo")

    with uow() as u:
        [event] = u.events.list(kind=EventKind.SCENARIO_INJECTED)
    assert event.inputs["name"] == "drought"
    assert event.inputs["et0_multiplier"] == 2.0
    assert sim.active_scenarios(T0) == (drought,)
