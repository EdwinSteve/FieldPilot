"""Implements the agent's `FieldReader` port over stored facts (§4.8)."""

from collections.abc import Callable, Sequence
from datetime import datetime

from app.agent.field import IrrigationRecord, MoistureReading, StageView, ZoneView
from app.domain.enums import SensorKind, TaskStatus
from app.domain.errors import MissingDataError
from app.domain.models import Task, Zone
from app.persistence.ports import UnitOfWork
from app.phenology.catalog import CropCatalog
from app.phenology.gdd import crop_coefficient_at, stage_for
from app.safety.rules import IRRIGATION_ACTIONS
from app.services.gate_context import RainForecast, active_cycle, volume_mm
from app.simulator.clock import Clock

UowFactory = Callable[[], UnitOfWork]

_UPCOMING = frozenset({TaskStatus.SCHEDULED, TaskStatus.PENDING_APPROVAL})


class StoredFieldReader:
    def __init__(
        self, uow: UowFactory, forecast: RainForecast, crops: CropCatalog, clock: Clock
    ) -> None:
        self._uow = uow
        self._forecast = forecast
        self._crops = crops
        self._clock = clock

    def zones(self, plot_id: int) -> Sequence[ZoneView]:
        with self._uow() as u:
            tasks = _irrigations(u, plot_id)
            return [self._view(u, zone, tasks) for zone in u.zones.list_by_plot(plot_id)]

    def zone(self, plot_id: int, zone_id: int) -> ZoneView | None:
        with self._uow() as u:
            zone = next((z for z in u.zones.list_by_plot(plot_id) if z.id == zone_id), None)
            return None if zone is None else self._view(u, zone, _irrigations(u, plot_id))

    def rain_mm_next_24h(self, plot_id: int, at: datetime) -> float | None:
        return self._forecast.rain_mm_next_24h(plot_id, at)

    def crop_stage(self, plot_id: int) -> StageView:
        with self._uow() as u:
            cycle = active_cycle(u, plot_id)
        crop = self._crops[cycle.crop]
        stage = stage_for(cycle.accumulated_gdd, crop)
        return StageView(
            cycle_id=_stored(cycle.id, "cycle"),
            stage=stage.name,
            stage_display_es=stage.display_name.get("es", stage.name),
            accumulated_gdd=cycle.accumulated_gdd,
            kc=crop_coefficient_at(cycle.accumulated_gdd, crop),
        )

    def _view(self, u: UnitOfWork, zone: Zone, tasks: Sequence[Task]) -> ZoneView:
        zone_id = _stored(zone.id, "zone")
        mine = [task for task in tasks if task.zone_id == zone_id]
        now = self._clock.now()
        executed = [t for t in mine if t.status is TaskStatus.EXECUTED and t.scheduled_for <= now]
        last = max(executed, key=lambda t: t.scheduled_for, default=None)
        upcoming = sorted((t for t in mine if t.status in _UPCOMING), key=lambda t: t.scheduled_for)
        return ZoneView(
            zone_id=zone_id,
            name=zone.name,
            field_capacity_pct=zone.field_capacity_pct,
            moisture=_latest_moisture(u, zone_id),
            last_irrigation=None if last is None else _record(last),
            upcoming=tuple(_record(task) for task in upcoming),
        )


def _irrigations(u: UnitOfWork, plot_id: int) -> list[Task]:
    cycle = active_cycle(u, plot_id)
    return [t for t in u.tasks.list(cycle_id=cycle.id) if t.action_type in IRRIGATION_ACTIONS]


def _latest_moisture(u: UnitOfWork, zone_id: int) -> MoistureReading | None:
    for sensor in u.sensors.list_by_zone(zone_id):
        if sensor.kind is SensorKind.SOIL_MOISTURE and sensor.id is not None:
            reading = u.readings.latest(sensor.id)
            if reading is not None and reading.id is not None:
                return MoistureReading(reading.id, reading.value, reading.recorded_at)
    return None


def _record(task: Task) -> IrrigationRecord:
    return IrrigationRecord(
        task_id=_stored(task.id, "task"),
        action_type=str(task.action_type),
        volume_mm=volume_mm(task),
        scheduled_for=task.scheduled_for,
        status=str(task.status),
    )


def _stored(entity_id: int | None, entity: str) -> int:
    if entity_id is None:
        raise MissingDataError(f"an unsaved {entity} reached the field reader")
    return entity_id
