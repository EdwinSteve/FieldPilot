"""SimulationTicker: readings, due tasks and degree-days, only when asked (D065)."""

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

from app.domain.enums import ActionType, SensorKind, TaskStatus
from app.domain.models import Reading, Sensor, Zone
from app.persistence.unit_of_work import SqlUnitOfWork
from app.services.phenology import PhenologyService
from app.services.ticker import SimulationTicker
from app.simulator.field import FieldSimulator
from tests.integration.services.world import CROPS, DAY1, World

UowFactory = Callable[[], SqlUnitOfWork]


def _ticker(world: World, simulator: FieldSimulator | None = None) -> SimulationTicker:
    return SimulationTicker(
        world.uow,
        world.clock,
        simulator or world.valves,
        world.due,
        PhenologyService(world.uow, CROPS, world.clock),
    )


def _moisture_readings(world: World) -> list[Reading]:
    with world.uow() as u:
        [sensor] = [
            s for s in u.sensors.list_by_zone(world.zone_id) if s.kind is SensorKind.SOIL_MOISTURE
        ]
        assert sensor.id is not None
        return list(u.readings.list_for_sensor(sensor.id))


def test_a_tick_records_one_reading_per_sensor(uow: UowFactory) -> None:
    world = World(uow)
    world.clock.advance(timedelta(minutes=30))

    result = _ticker(world).tick()

    assert result.readings_recorded == 1
    assert result.at == DAY1 + timedelta(minutes=30)
    assert [r.recorded_at for r in _moisture_readings(world)][-1] <= result.at


def test_a_second_tick_at_the_same_time_records_nothing(uow: UowFactory) -> None:
    world = World(uow)
    world.clock.advance(timedelta(minutes=30))
    ticker = _ticker(world)

    ticker.tick()
    again = ticker.tick()

    assert again.readings_recorded == 0
    assert again.tasks == () and again.days_counted == ()


def test_after_a_restart_zones_are_rebuilt_from_their_latest_reading(uow: UowFactory) -> None:
    """D014: the simulator starts empty; D019: a zone without data is not invented."""
    world = World(uow)
    with uow() as u:
        bare = u.zones.add(Zone(world.plot_id, "Sin sensor", 0.5, 30.0, valve_id="v9"))
        u.commit()
    empty = FieldSimulator(start=DAY1)
    world.clock.advance(timedelta(minutes=30))

    result = _ticker(world, empty).tick()

    assert empty.simulates(world.zone_id)
    assert bare.id is not None and not empty.simulates(bare.id)
    assert result.zones_without_data == (bare.id,)
    assert result.readings_recorded == 1


def test_a_tick_runs_the_tasks_that_are_due(uow: UowFactory) -> None:
    world = World(uow)
    later = world.proposals.propose(
        world.action(ActionType.EXTRA_IRRIGATION, volume_mm=10.0, at=DAY1 + timedelta(hours=1))
    )
    assert later.task.status is TaskStatus.SCHEDULED

    world.clock.advance(timedelta(hours=1))
    result = _ticker(world).tick()

    assert [(t.id, t.status) for t in result.tasks] == [(later.task.id, TaskStatus.EXECUTED)]


def test_ended_days_with_temperatures_are_counted_once(uow: UowFactory) -> None:
    world = World(uow)
    with uow() as u:
        sensor = u.sensors.add(Sensor(world.zone_id, SensorKind.TEMPERATURE, "C"))
        assert sensor.id is not None
        # Local day 2026-10-27 in Neiva (UTC-5) runs 05:00 to 05:00 UTC.
        u.readings.add_many(
            [
                Reading(sensor.id, 16.0, datetime(2026, 10, 27, 10, 0, tzinfo=UTC)),
                Reading(sensor.id, 30.0, datetime(2026, 10, 27, 20, 0, tzinfo=UTC)),
            ]
        )
        u.commit()
    ticker = _ticker(world)

    first = ticker.tick()
    second = ticker.tick()

    assert first.days_counted == (date(2026, 10, 27),)  # earlier days have no data
    assert second.days_counted == ()
    with uow() as u:
        assert u.cycles.list_by_plot(world.plot_id)[0].gdd_updated_through == date(2026, 10, 27)
