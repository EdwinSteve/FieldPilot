"""StoredFieldReader: the agent's view of the field, from stored facts."""

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

import pytest

from app.agent.field import IrrigationRecord, MoistureReading
from app.domain.enums import ActionType, EventKind, SensorKind, TaskStatus
from app.domain.errors import MissingDataError
from app.domain.models import Plot, Reading, Sensor, Zone
from app.persistence.unit_of_work import SqlUnitOfWork
from app.phenology.catalog import CropSpec
from app.services.field_reader import StoredFieldReader
from tests.conftest import T0, FieldIds, later, make_event, make_task
from tests.fakes import FakeClock

UowFactory = Callable[[], SqlUnitOfWork]


class FixedRain:
    def rain_mm_next_24h(self, plot_id: int, at: datetime) -> float | None:
        return 2.5


NOW = later(120)


def _reader(uow: UowFactory, maize: CropSpec) -> StoredFieldReader:
    return StoredFieldReader(uow, FixedRain(), {"maize": maize}, FakeClock(NOW))


def _add_reading(uow: UowFactory, zone_id: int, value: float, minutes: int) -> int:
    with uow() as u:
        sensors = [s for s in u.sensors.list_by_zone(zone_id) if s.kind is SensorKind.SOIL_MOISTURE]
        sensor = (
            sensors[0] if sensors else u.sensors.add(Sensor(zone_id, SensorKind.SOIL_MOISTURE, "%"))
        )
        assert sensor.id is not None
        [reading] = u.readings.add_many([Reading(sensor.id, value, later(minutes))])
        u.commit()
    assert reading.id is not None
    return reading.id


def _add_task(
    uow: UowFactory,
    field: FieldIds,
    status: TaskStatus,
    at: datetime,
    action: ActionType = ActionType.IRRIGATION,
) -> int:
    initial = TaskStatus.SCHEDULED if status is TaskStatus.EXECUTED else status
    task = replace(make_task(field, initial), scheduled_for=at, action_type=action)
    with uow() as u:
        stored = u.tasks.add(task, make_event(EventKind.PROPOSAL))
        assert stored.id is not None
        if status is TaskStatus.EXECUTED:
            u.tasks.transition(stored.id, TaskStatus.EXECUTED, make_event(EventKind.EXECUTION))
        u.commit()
    return stored.id


def test_a_zone_shows_its_latest_moisture_and_capacity(
    uow: UowFactory, field: FieldIds, maize: CropSpec
) -> None:
    _add_reading(uow, field.zone_id, 38.0, 0)
    latest = _add_reading(uow, field.zone_id, 21.0, 60)

    zone = _reader(uow, maize).zone(field.plot_id, field.zone_id)

    assert zone is not None
    assert zone.moisture == MoistureReading(latest, 21.0, later(60))
    assert zone.field_capacity_pct == 32.0
    assert zone.name == "Zone 2"


def test_last_irrigation_is_the_latest_executed_one(
    uow: UowFactory, field: FieldIds, maize: CropSpec
) -> None:
    _add_task(uow, field, TaskStatus.EXECUTED, T0)
    latest = _add_task(uow, field, TaskStatus.EXECUTED, later(30))
    _add_task(uow, field, TaskStatus.SCHEDULED, later(90))  # due but not executed
    scheduled = _add_task(
        uow, field, TaskStatus.SCHEDULED, later(24 * 60), ActionType.EXTRA_IRRIGATION
    )
    pending = _add_task(uow, field, TaskStatus.PENDING_APPROVAL, later(12 * 60))

    zone = _reader(uow, maize).zone(field.plot_id, field.zone_id)

    assert zone is not None
    assert zone.last_irrigation == IrrigationRecord(
        latest, "irrigation", 15.0, later(30), "executed"
    )
    assert [t.task_id for t in zone.upcoming][-2:] == [pending, scheduled]
    assert zone.upcoming[-1].action_type == "extra_irrigation"


def test_non_irrigation_tasks_are_not_shown(
    uow: UowFactory, field: FieldIds, maize: CropSpec
) -> None:
    _add_task(uow, field, TaskStatus.PENDING_APPROVAL, later(60), ActionType.FERTILIZER)

    zone = _reader(uow, maize).zone(field.plot_id, field.zone_id)

    assert zone is not None and zone.upcoming == () and zone.last_irrigation is None


def test_a_zone_of_another_plot_is_none(uow: UowFactory, field: FieldIds, maize: CropSpec) -> None:
    with uow() as u:
        other = u.plots.add(Plot("Other", 4.6, -74.1, 1.0, created_at=T0, utc_offset_hours=-5.0))
        assert other.id is not None
        foreign = u.zones.add(Zone(other.id, "Far", 1.0, 30.0, valve_id="valve-9"))
        u.commit()
    assert foreign.id is not None

    assert _reader(uow, maize).zone(field.plot_id, foreign.id) is None
    assert [z.zone_id for z in _reader(uow, maize).zones(field.plot_id)] == [field.zone_id]


def test_crop_stage_comes_from_the_accumulated_gdd(
    uow: UowFactory, field: FieldIds, maize: CropSpec
) -> None:
    with uow() as u:
        cycle = u.cycles.get(field.cycle_id)
        u.cycles.update(replace(cycle, accumulated_gdd=600.0))
        u.commit()

    stage = _reader(uow, maize).crop_stage(field.plot_id)

    assert stage.cycle_id == field.cycle_id
    assert stage.accumulated_gdd == 600.0
    assert stage.stage == "vegetative"
    assert stage.stage_display_es
    assert 0 < stage.kc < 2


def test_the_forecast_goes_through_the_rain_port(
    uow: UowFactory, field: FieldIds, maize: CropSpec
) -> None:
    assert _reader(uow, maize).rain_mm_next_24h(field.plot_id, T0) == 2.5


def test_a_plot_without_an_active_cycle_is_missing_data(uow: UowFactory, maize: CropSpec) -> None:
    with uow() as u:
        plot = u.plots.add(Plot("Fallow", 2.9, -75.3, 1.0, created_at=T0, utc_offset_hours=-5.0))
        assert plot.id is not None
        u.commit()

    with pytest.raises(MissingDataError, match="no active crop cycle"):
        _reader(uow, maize).crop_stage(plot.id)
