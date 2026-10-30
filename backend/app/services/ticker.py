"""One step of the simulation, only when asked (D065).

At the current simulated time: record the simulator's readings, run the
tasks that are due, and count the degree-days of every local day that has
ended. Running it twice for the same simulated time changes nothing more.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.domain.errors import MissingDataError
from app.domain.models import CropCycle, Plot, Task
from app.persistence.ports import UnitOfWork
from app.services.due_tasks import DueTaskRunner
from app.services.gate_context import local_day
from app.services.phenology import PhenologyService
from app.services.simulation import ensure_simulated, record_readings
from app.simulator.clock import Clock
from app.simulator.field import FieldSimulator

UowFactory = Callable[[], UnitOfWork]


@dataclass(frozen=True)
class TickResult:
    at: datetime
    readings_recorded: int
    tasks: tuple[Task, ...]  # due tasks, executed or failed
    days_counted: tuple[date, ...]
    zones_without_data: tuple[int, ...]  # never simulated: no reading to start from (D019)


class SimulationTicker:
    def __init__(
        self,
        uow: UowFactory,
        clock: Clock,
        simulator: FieldSimulator,
        due: DueTaskRunner,
        phenology: PhenologyService,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._simulator = simulator
        self._due = due
        self._phenology = phenology

    def tick(self) -> TickResult:
        at = self._clock.now()
        with self._uow() as u:
            plots = list(u.plots.list())
            cycles = [c for p in plots if p.id is not None for c in u.cycles.list_by_plot(p.id)]
        missing = ensure_simulated(self._uow, self._simulator)
        readings = sum(self._record(plot, at) for plot in plots)
        tasks = tuple(self._due.run_due(at))
        days = tuple(d for cycle in cycles for d in self._count_days(cycle, plots, at))
        return TickResult(at, readings, tasks, days, tuple(missing))

    def _record(self, plot: Plot, at: datetime) -> int:
        """Readings at `at` for the simulated zones, unless this time is already recorded."""
        if plot.id is None or self._recorded_since(plot.id, at):
            return 0
        with self._uow() as u:
            zones = [z.id for z in u.zones.list_by_plot(plot.id) if z.id is not None]
        simulated = [zone_id for zone_id in zones if self._simulator.simulates(zone_id)]
        stored = record_readings(self._simulator, self._uow, self._clock, plot.id, simulated)
        return len(stored)

    def _recorded_since(self, plot_id: int, at: datetime) -> bool:
        with self._uow() as u:
            for zone in u.zones.list_by_plot(plot_id):
                if zone.id is None or not self._simulator.simulates(zone.id):
                    continue
                for sensor in u.sensors.list_by_zone(zone.id):
                    latest = u.readings.latest(sensor.id) if sensor.id is not None else None
                    if latest is not None and latest.recorded_at >= at:
                        return True
        return False

    def _count_days(self, cycle: CropCycle, plots: list[Plot], at: datetime) -> list[date]:
        """Every ended local day not yet counted. A day without temperatures is skipped;
        phenology records it as a gap when a later day is counted (D019)."""
        plot = next(p for p in plots if p.id == cycle.plot_id)
        if cycle.id is None:
            return []
        counted_through = cycle.gdd_updated_through
        first = counted_through + timedelta(days=1) if counted_through else cycle.sowing_date
        last = local_day(at, plot) - timedelta(days=1)
        counted = []
        day = first
        while day <= last:
            try:
                update = self._phenology.update_cycle(cycle.id, day)
            except MissingDataError:
                update = None
            if update is not None and not update.already_processed:
                counted.append(day)
            day += timedelta(days=1)
        return counted
