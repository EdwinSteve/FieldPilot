"""Build the gate's context from stored facts only, never from the caller (D035)."""

from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime, timedelta
from typing import Protocol

from app.autonomy.gate import GateContext
from app.domain.enums import CycleStatus, EventKind, SensorKind, TaskStatus
from app.domain.errors import MissingDataError
from app.domain.models import CropCycle, JsonValue, Plot, Task
from app.domain.proposals import ParamValue, ProposedAction
from app.persistence.ports import UnitOfWork
from app.phenology.catalog import CropCatalog
from app.phenology.gdd import stage_for
from app.safety.rules import IRRIGATION_ACTIONS, SafetyContext

UowFactory = Callable[[], UnitOfWork]

# Statuses whose irrigation counts toward the cap and the interval (D035, D040).
_COMMITTED = frozenset({TaskStatus.SCHEDULED, TaskStatus.EXECUTED})


class RainForecast(Protocol):
    def rain_mm_next_24h(self, plot_id: int, at: datetime) -> float | None: ...


class GateContextProvider(Protocol):
    def context_for(
        self, action: ProposedAction, exclude_task_id: int | None = None
    ) -> GateContext: ...


class StoredGateContextProvider:
    """Reads the emergency flag, soil moisture, forecast, stage and committed water."""

    def __init__(self, uow: UowFactory, forecast: RainForecast, crops: CropCatalog) -> None:
        self._uow = uow
        self._forecast = forecast
        self._crops = crops

    def context_for(
        self, action: ProposedAction, exclude_task_id: int | None = None
    ) -> GateContext:
        """`exclude_task_id` keeps a scheduled task from counting itself when re-evaluated."""
        with self._uow() as u:
            plot = u.plots.get(action.plot_id)
            cycle = active_cycle(u, action.plot_id)
            moisture, field_capacity = self._moisture(u, action.zone_id)
            counted = [
                (task, mm)
                for task, mm in _irrigation_water(u, cycle, action.zone_id)
                if task.id != exclude_task_id and mm > 0
            ]
            stop_active = u.control.get().emergency_stop_active
        day = local_day(action.scheduled_for, plot)
        safety = SafetyContext(
            emergency_stop_active=stop_active,
            irrigated_mm_on_day=sum(
                mm for task, mm in counted if local_day(task.scheduled_for, plot) == day
            ),
            last_irrigation_at=_nearest(
                action.scheduled_for, [t.scheduled_for for t, _ in counted]
            ),
            soil_moisture_vwc=moisture,
            field_capacity_vwc=field_capacity,
            rain_forecast_mm_24h=self._forecast.rain_mm_next_24h(
                action.plot_id, action.scheduled_for
            ),
        )
        stage = stage_for(cycle.accumulated_gdd, self._crops[cycle.crop])
        return GateContext(safety, stage.level_for(action.action_type))

    def _moisture(self, u: UnitOfWork, zone_id: int | None) -> tuple[float | None, float | None]:
        if zone_id is None:
            return None, None
        zone = u.zones.get(zone_id)
        for sensor in u.sensors.list_by_zone(zone_id):
            if sensor.kind is SensorKind.SOIL_MOISTURE and sensor.id is not None:
                reading = u.readings.latest(sensor.id)
                if reading is not None:
                    return reading.value, zone.field_capacity_pct
        return None, zone.field_capacity_pct


def active_cycle(u: UnitOfWork, plot_id: int) -> CropCycle:
    for cycle in u.cycles.list_by_plot(plot_id):
        if cycle.status is CycleStatus.ACTIVE:
            return cycle
    raise MissingDataError(f"plot {plot_id} has no active crop cycle")


def local_day(at: datetime, plot: Plot) -> date:
    """The plot's local calendar day of `at` (D018)."""
    return (at + timedelta(hours=plot.utc_offset_hours)).date()


def action_for_task(u: UnitOfWork, task: Task, proposed_by: str) -> ProposedAction:
    """Rebuild the proposal behind a stored task; same content gives the same key (D023)."""
    plot = u.plots.get(u.cycles.get(task.cycle_id).plot_id)
    if plot.id is None:
        raise MissingDataError(f"task {task.id} has no stored plot")
    return ProposedAction.create(
        action_type=task.action_type,
        plot_id=plot.id,
        zone_id=task.zone_id,
        scheduled_for=task.scheduled_for,
        local_day=local_day(task.scheduled_for, plot),
        params=_params(task.params),
        rationale=task.rationale,
        proposed_by=proposed_by,
        estimated_cost=task.estimated_cost,
    )


def volume_mm(task: Task) -> float:
    value = task.params.get("volume_mm")
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return 0.0


def _irrigation_water(
    u: UnitOfWork, cycle: CropCycle, zone_id: int | None
) -> list[tuple[Task, float]]:
    """Each irrigation of the zone with the water it counts for (D035, D040)."""
    if zone_id is None:
        return []
    water: list[tuple[Task, float]] = []
    for task in u.tasks.list(cycle_id=cycle.id):
        if task.zone_id != zone_id or task.action_type not in IRRIGATION_ACTIONS:
            continue
        if task.status in _COMMITTED:
            water.append((task, volume_mm(task)))
        elif task.status is TaskStatus.REVERTED and task.id is not None:
            water.append((task, _applied_before_revert(u, task.id)))
    return water


def _applied_before_revert(u: UnitOfWork, task_id: int) -> float:
    for event in u.events.list(task_id=task_id, kind=EventKind.REVERT):
        applied = event.inputs.get("applied_mm")
        if isinstance(applied, int | float) and not isinstance(applied, bool):
            return float(applied)
    return 0.0


def _nearest(target: datetime, times: Sequence[datetime]) -> datetime | None:
    """The committed irrigation closest in time, before or after (D035)."""
    return min(times, key=lambda t: abs(t - target), default=None)


def _params(params: Mapping[str, JsonValue]) -> dict[str, ParamValue]:
    return {
        name: float(value) if isinstance(value, int | float) else str(value)
        for name, value in params.items()
        if not isinstance(value, bool | list | dict) and value is not None
    }
