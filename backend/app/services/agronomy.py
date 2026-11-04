"""The agronomist's view beyond water, over stored facts (D093).

- Microclimate: the zone's own temperature and humidity readings.
- Soil: pH and organic carbon from SoilGrids when the plot has site data,
  otherwise the demo probe; N-P-K from the simulated probe (D038): the
  starting value, minus the crop's uptake by degree-days, plus the
  fertilizer tasks the farmer approved that are due.
- Tasks: the plot's open tasks, and cancelling an agent's task that has not run.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.agent.field import Microclimate, SoilTarget, SoilView, TaskNotCancellableError, TaskRecord
from app.domain.enums import ActionType, EventKind, SensorKind, TaskStatus
from app.domain.errors import ConfigError, MissingDataError
from app.domain.models import Event, Reading, Task
from app.persistence.ports import UnitOfWork
from app.planning.ports import SiteSource
from app.services.gate_context import active_cycle
from app.simulator.clock import Clock

UowFactory = Callable[[], UnitOfWork]
WINDOW = timedelta(hours=48)
MAX_GAP = timedelta(hours=2)  # a longer gap between readings is not counted as humid
HUMID_RH_PCT = 90.0
HUMID_T_RANGE_C = (10.0, 30.0)
NUTRIENTS = ("nitrogen", "phosphorus", "potassium")
_OPEN = frozenset({TaskStatus.PENDING_APPROVAL, TaskStatus.SCHEDULED})
_APPLIED = frozenset({TaskStatus.SCHEDULED, TaskStatus.EXECUTED})  # approved, or done
_SOC, _PH = 2, 3  # SoilGrids columns: sand, clay, soc, phh2o, ... (planner PROPERTIES)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _ProbeZone(_Strict):
    ph: float = Field(gt=0, lt=14)
    organic_carbon_g_kg: float = Field(ge=0)
    nitrogen_ppm: float = Field(ge=0)
    phosphorus_ppm: float = Field(ge=0)
    potassium_ppm: float = Field(ge=0)


class _Targets(_Strict):
    ph: tuple[float, float]
    nitrogen: tuple[float, float]
    phosphorus: tuple[float, float]
    potassium: tuple[float, float]


class _ProbeFile(_Strict):
    zones: list[_ProbeZone] = Field(min_length=1)
    uptake_ppm_per_100_gdd: dict[str, float]
    ppm_per_kg_ha_of_nutrient: float = Field(gt=0)
    products: dict[str, dict[str, float]]
    targets: dict[str, _Targets]


@dataclass(frozen=True)
class SoilProbe:
    zones: tuple[_ProbeZone, ...]
    uptake: Mapping[str, float]
    ppm_per_kg_ha: float
    products: Mapping[str, Mapping[str, float]]
    targets: Mapping[str, _Targets]

    def zone(self, index: int) -> _ProbeZone:
        return self.zones[min(index, len(self.zones) - 1)]

    def targets_for(self, crop: str) -> dict[str, SoilTarget]:
        chosen = self.targets.get(crop) or self.targets["default"]
        return {name: SoilTarget(*getattr(chosen, name)) for name in ("ph", *NUTRIENTS)}

    def shares(self, product: str) -> Mapping[str, float]:
        name = product.lower()
        for key, shares in self.products.items():
            if key != "default" and key in name:
                return shares
        return self.products.get("default", {})


def load_soil_probe(path: Path) -> SoilProbe:
    try:
        parsed = _ProbeFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise ConfigError(f"{path.name}: {error}") from error
    if "default" not in parsed.targets:
        raise ConfigError(f"{path.name}: targets needs a default entry")
    return SoilProbe(tuple(parsed.zones), parsed.uptake_ppm_per_100_gdd,
                     parsed.ppm_per_kg_ha_of_nutrient, parsed.products,
                     parsed.targets)  # fmt: skip


class StoredAgronomy:
    def __init__(
        self, uow: UowFactory, clock: Clock, probe: SoilProbe, sites: SiteSource | None
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._probe = probe
        self._sites = sites

    # --- microclimate ------------------------------------------------------------------

    def microclimate(self, plot_id: int, zone_id: int, at: datetime) -> Microclimate | None:
        with self._uow() as u:
            if not any(z.id == zone_id for z in u.zones.list_by_plot(plot_id)):
                return None
            series: dict[SensorKind, Sequence[Reading]] = {}
            for sensor in u.sensors.list_by_zone(zone_id):
                if sensor.id is not None and sensor.kind in (SensorKind.TEMPERATURE,
                                                             SensorKind.HUMIDITY):  # fmt: skip
                    series[sensor.kind] = u.readings.list_for_sensor(sensor.id, at - WINDOW, at)
        return summarize(zone_id, series.get(SensorKind.TEMPERATURE, ()),
                         series.get(SensorKind.HUMIDITY, ()), at)  # fmt: skip

    # --- soil --------------------------------------------------------------------------

    def soil(self, plot_id: int, zone_id: int, at: datetime) -> SoilView | None:
        with self._uow() as u:
            plot = u.plots.get(plot_id)
            zones = [z.id for z in u.zones.list_by_plot(plot_id)]
            if zone_id not in zones:
                return None
            cycle = active_cycle(u, plot_id)
            tasks = [t for t in u.tasks.list(cycle_id=cycle.id)
                     if t.action_type is ActionType.FERTILIZER]  # fmt: skip
        probe = self._probe.zone(zones.index(zone_id))
        ph, carbon, source = probe.ph, probe.organic_carbon_g_kg, "probe"
        if self._sites is not None:
            try:
                topsoil = self._sites.site(plot).snapshot.soil_profile[0]
                ph, carbon, source = float(topsoil[_PH]), float(topsoil[_SOC]), "soilgrids"
            except MissingDataError:
                pass
        added = self._fertilized(tasks, zone_id, at)
        gdd = cycle.accumulated_gdd
        values = {
            name: max(0.0, getattr(probe, f"{name}_ppm") - self._probe.uptake.get(name, 0.0)
                      * gdd / 100 + added.get(name, 0.0))
            for name in NUTRIENTS
        }  # fmt: skip
        return SoilView(zone_id, ph, source, carbon, values["nitrogen"], values["phosphorus"],
                        values["potassium"], self._probe.targets_for(cycle.crop),
                        simulated=True)  # fmt: skip

    def _fertilized(self, tasks: Sequence[Task], zone_id: int, at: datetime) -> dict[str, float]:
        added: dict[str, float] = {}
        for task in tasks:
            if task.status not in _APPLIED or task.scheduled_for > at:
                continue
            if task.zone_id not in (None, zone_id):
                continue
            dose = task.params.get("dose_kg_ha")
            if not isinstance(dose, int | float) or isinstance(dose, bool):
                continue
            for nutrient, share in self._probe.shares(str(task.params.get("product", ""))).items():
                added[nutrient] = added.get(nutrient, 0.0) + float(dose) * share * (
                    self._probe.ppm_per_kg_ha
                )
        return added

    # --- tasks -------------------------------------------------------------------------

    def open_tasks(self, plot_id: int) -> Sequence[TaskRecord]:
        with self._uow() as u:
            cycle = active_cycle(u, plot_id)
            tasks = [t for t in u.tasks.list(cycle_id=cycle.id) if t.status in _OPEN]
            return [_record(t, _proposer(u, t)) for t in sorted(tasks, key=lambda t: t.id or 0)]

    def cancel(self, plot_id: int, task_id: int, reason: str, actor: str) -> TaskRecord:
        with self._uow() as u:
            cycle = active_cycle(u, plot_id)
            task = next((t for t in u.tasks.list(cycle_id=cycle.id) if t.id == task_id), None)
            if task is None:
                raise TaskNotCancellableError(f"Task {task_id} is not in this plot's cycle.")
            proposer = _proposer(u, task)
            if not proposer.startswith("agent:"):
                raise TaskNotCancellableError(
                    f"Task {task_id} was proposed by {proposer}; only an agent's task can be "
                    "cancelled by an agent."
                )
            if task.status not in _OPEN:
                raise TaskNotCancellableError(f"Task {task_id} is {task.status}: it cannot be "
                                              "cancelled.")  # fmt: skip
            if task.status is TaskStatus.SCHEDULED and _requested(u, task_id):
                raise TaskNotCancellableError(f"Task {task_id} has started: revert it instead.")
            stored = u.tasks.transition(
                task_id,
                TaskStatus.CANCELLED,
                Event(
                    kind=EventKind.TASK_CANCELLED,
                    actor=actor,
                    reason=reason,
                    occurred_at=self._clock.now(),
                    inputs={"previous_status": str(task.status)},
                ),
            )
            u.commit()
            return _record(stored, proposer)


def summarize(
    zone_id: int, temperature: Sequence[Reading], humidity: Sequence[Reading], until: datetime
) -> Microclimate:
    """Pairs the two series by time; humid-leaf hours count the gaps after a humid reading."""
    t_by_time = {r.recorded_at: r.value for r in temperature}
    pairs = [(r, t_by_time[r.recorded_at]) for r in humidity if r.recorded_at in t_by_time]
    if not pairs:
        return Microclimate(zone_id, WINDOW / timedelta(hours=1), 0, None, None, None, None,
                            None, None, until)  # fmt: skip
    humid = timedelta()
    for (reading, t), following in zip(pairs, [*pairs[1:], None], strict=True):
        end = until if following is None else following[0].recorded_at
        low, high = HUMID_T_RANGE_C
        if reading.value >= HUMID_RH_PCT and low <= t <= high:
            humid += min(end - reading.recorded_at, MAX_GAP)
    temps = [t for _, t in pairs]
    rhs = [r.value for r, _ in pairs]
    return Microclimate(
        zone_id=zone_id,
        window_hours=WINDOW / timedelta(hours=1),
        readings=len(pairs),
        temperature_mean_c=sum(temps) / len(temps),
        temperature_max_c=max(temps),
        humidity_mean_pct=sum(rhs) / len(rhs),
        humidity_max_pct=max(rhs),
        humid_leaf_hours=humid / timedelta(hours=1),
        last_reading_id=pairs[-1][0].id,
        until=until,
    )


def _proposer(u: UnitOfWork, task: Task) -> str:
    if task.id is None:
        return "unknown"
    proposals = u.events.list(task_id=task.id, kind=EventKind.PROPOSAL)
    return proposals[0].actor if proposals else "unknown"


def _requested(u: UnitOfWork, task_id: int) -> bool:
    return bool(u.events.list(task_id=task_id, kind=EventKind.EXECUTION_REQUESTED))


def _record(task: Task, proposer: str) -> TaskRecord:
    if task.id is None:
        raise MissingDataError("an unsaved task reached the agronomist")
    params = {k: v for k, v in task.params.items() if isinstance(v, int | float | str)
              and not isinstance(v, bool)}  # fmt: skip
    return TaskRecord(task.id, str(task.action_type), task.zone_id, task.scheduled_for,
                      str(task.status), proposer, dict(params),
                      task.rationale)  # fmt: skip
