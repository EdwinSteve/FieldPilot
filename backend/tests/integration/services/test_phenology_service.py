from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta

import pytest

from app.domain.enums import EventKind, SensorKind
from app.domain.errors import DayNotFinishedError, MissingDataError
from app.domain.models import Reading, Sensor
from app.persistence.unit_of_work import SqlUnitOfWork
from app.phenology.catalog import CropSpec
from app.phenology.gdd import daily_gdd
from app.services.phenology import PhenologyService
from app.simulator.clock import SimClock
from tests.conftest import FieldIds
from tests.fakes import FakeWall

UowFactory = Callable[[], SqlUnitOfWork]
UTC_OFFSET = -5.0  # the field fixture's plot (Neiva, Huila)
SOWING = date(2026, 10, 1)
DAY1, DAY2, DAY3 = SOWING, SOWING + timedelta(days=1), SOWING + timedelta(days=2)


def local(day: date, hour: int) -> datetime:
    """A local wall-clock time in the plot's zone, as aware UTC."""
    return datetime.combine(day, time(hour), tzinfo=UTC) - timedelta(hours=UTC_OFFSET)


@pytest.fixture
def sensor_id(uow: UowFactory, field: FieldIds) -> int:
    with uow() as u:
        sensor = u.sensors.add(Sensor(field.zone_id, SensorKind.TEMPERATURE, "C"))
        u.commit()
    assert sensor.id is not None
    return sensor.id


def add_temperatures(uow: UowFactory, sensor_id: int, values: list[tuple[datetime, float]]) -> None:
    with uow() as u:
        u.readings.add_many([Reading(sensor_id, value, at) for at, value in values])
        u.commit()


def typical_day(uow: UowFactory, sensor_id: int, day: date, low: float, high: float) -> None:
    add_temperatures(uow, sensor_id, [(local(day, 5), low), (local(day, 15), high)])


def service(uow: UowFactory, maize: CropSpec, now: datetime) -> PhenologyService:
    clock = SimClock.start(now, FakeWall(now), paused=True)
    return PhenologyService(uow, {"maize": maize}, clock)


def later_than_all_days() -> datetime:
    return local(SOWING + timedelta(days=10), 0)


def cycle_state(uow: UowFactory, cycle_id: int) -> tuple[float, date | None]:
    with uow() as u:
        cycle = u.cycles.get(cycle_id)
    return cycle.accumulated_gdd, cycle.gdd_updated_through


def events(uow: UowFactory, kind: EventKind) -> list[dict[str, object]]:
    with uow() as u:
        return [dict(e.inputs) for e in u.events.list(kind=kind)]


def test_a_day_adds_its_gdd_and_opens_the_first_stage(
    uow: UowFactory, field: FieldIds, sensor_id: int, maize: CropSpec
) -> None:
    typical_day(uow, sensor_id, DAY1, low=22.0, high=34.0)

    result = service(uow, maize, later_than_all_days()).update_cycle(field.cycle_id, DAY1)

    assert result.gdd_added == pytest.approx(16.0)
    assert cycle_state(uow, field.cycle_id) == (pytest.approx(16.0), DAY1)
    with uow() as u:
        assert [s.name for s in u.stages.list_by_cycle(field.cycle_id)] == ["sowing"]


def test_processing_the_same_day_twice_counts_it_once(
    uow: UowFactory, field: FieldIds, sensor_id: int, maize: CropSpec
) -> None:
    typical_day(uow, sensor_id, DAY1, low=22.0, high=34.0)
    phenology = service(uow, maize, later_than_all_days())

    phenology.update_cycle(field.cycle_id, DAY1)
    second = phenology.update_cycle(field.cycle_id, DAY1)

    assert second.already_processed is True
    assert cycle_state(uow, field.cycle_id)[0] == pytest.approx(16.0)


def test_a_minimum_at_22h_local_stays_in_its_local_day(
    uow: UowFactory, field: FieldIds, sensor_id: int, maize: CropSpec
) -> None:
    # 22:00 local on DAY1 is 03:00 UTC on DAY2; it must still count for DAY1.
    add_temperatures(
        uow,
        sensor_id,
        [
            (local(DAY1, 15), 28.0),
            (local(DAY1, 22), 12.0),  # DAY1's minimum
            (local(DAY2, 2), 4.0),  # colder, but belongs to DAY2
        ],
    )

    result = service(uow, maize, later_than_all_days()).update_cycle(field.cycle_id, DAY1)

    assert local(DAY1, 22).date() == DAY2  # the UTC date differs on purpose
    assert result.gdd_added == pytest.approx(daily_gdd(12.0, 28.0, maize))


def test_a_day_without_data_raises_and_writes_nothing(
    uow: UowFactory, field: FieldIds, sensor_id: int, maize: CropSpec
) -> None:
    typical_day(uow, sensor_id, DAY1, low=22.0, high=34.0)
    phenology = service(uow, maize, later_than_all_days())
    phenology.update_cycle(field.cycle_id, DAY1)
    before = cycle_state(uow, field.cycle_id)

    with pytest.raises(MissingDataError, match=str(DAY2)):
        phenology.update_cycle(field.cycle_id, DAY2)

    assert cycle_state(uow, field.cycle_id) == before
    assert events(uow, EventKind.PHENOLOGY_GAP) == []


def test_after_a_gap_the_next_day_counts_only_itself(
    uow: UowFactory, field: FieldIds, sensor_id: int, maize: CropSpec
) -> None:
    typical_day(uow, sensor_id, DAY1, low=22.0, high=34.0)  # 16 GDD
    typical_day(uow, sensor_id, DAY3, low=15.0, high=25.0)  # 10 GDD; DAY2 has no data
    phenology = service(uow, maize, later_than_all_days())
    phenology.update_cycle(field.cycle_id, DAY1)
    with pytest.raises(MissingDataError):
        phenology.update_cycle(field.cycle_id, DAY2)

    result = phenology.update_cycle(field.cycle_id, DAY3)

    assert result.gdd_added == pytest.approx(10.0)
    assert result.gap_days == (DAY2,)
    assert cycle_state(uow, field.cycle_id) == (pytest.approx(26.0), DAY3)
    assert events(uow, EventKind.PHENOLOGY_GAP) == [
        {"cycle_id": field.cycle_id, "missing_days": [DAY2.isoformat()]}
    ]


def test_late_data_for_a_gap_day_is_not_back_filled(
    uow: UowFactory, field: FieldIds, sensor_id: int, maize: CropSpec
) -> None:
    typical_day(uow, sensor_id, DAY1, low=22.0, high=34.0)
    typical_day(uow, sensor_id, DAY3, low=15.0, high=25.0)
    phenology = service(uow, maize, later_than_all_days())
    phenology.update_cycle(field.cycle_id, DAY1)
    phenology.update_cycle(field.cycle_id, DAY3)
    typical_day(uow, sensor_id, DAY2, low=22.0, high=34.0)  # arrives too late

    assert phenology.update_cycle(field.cycle_id, DAY2).already_processed is True
    assert cycle_state(uow, field.cycle_id)[0] == pytest.approx(26.0)


def test_an_unfinished_day_is_refused(
    uow: UowFactory, field: FieldIds, sensor_id: int, maize: CropSpec
) -> None:
    typical_day(uow, sensor_id, DAY1, low=22.0, high=34.0)

    with pytest.raises(DayNotFinishedError):
        service(uow, maize, local(DAY1, 20)).update_cycle(field.cycle_id, DAY1)


def test_a_day_before_sowing_is_refused(
    uow: UowFactory, field: FieldIds, sensor_id: int, maize: CropSpec
) -> None:
    with pytest.raises(ValueError, match="before the sowing date"):
        service(uow, maize, later_than_all_days()).update_cycle(
            field.cycle_id, SOWING - timedelta(days=1)
        )


def test_crossing_a_threshold_closes_one_stage_and_opens_the_next(
    uow: UowFactory, field: FieldIds, sensor_id: int, maize: CropSpec
) -> None:
    with uow() as u:  # cycle already at 45 GDD, in germination_emergence
        cycle = u.cycles.get(field.cycle_id)
        u.cycles.update(replace(cycle, accumulated_gdd=45.0, gdd_updated_through=DAY1))
        u.commit()
    typical_day(uow, sensor_id, DAY2, low=22.0, high=34.0)  # +16 -> 61, crosses 55.6

    result = service(uow, maize, later_than_all_days()).update_cycle(field.cycle_id, DAY2)

    assert result.entered_stages == ("vegetative",)
    with uow() as u:
        stages = u.stages.list_by_cycle(field.cycle_id)
    assert [(s.name, s.ended_at is None) for s in stages] == [
        ("germination_emergence", False),
        ("vegetative", True),
    ]
    [transition] = events(uow, EventKind.STAGE_TRANSITION)
    assert transition["from_stage"] == "germination_emergence"
    assert transition["to_stage"] == "vegetative"
    assert transition["gdd_before"] == pytest.approx(45.0)
    assert transition["gdd_after"] == pytest.approx(61.0)
