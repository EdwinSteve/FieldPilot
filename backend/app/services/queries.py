"""Read-only views for the API: what the dashboard shows, from stored facts only."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import timedelta

from app.domain.enums import EventKind, TaskStatus
from app.domain.models import (
    CropCycle,
    Event,
    Notification,
    Plot,
    Reading,
    Report,
    Sensor,
    Stage,
    Task,
    Zone,
)
from app.persistence.ports import UnitOfWork
from app.services.revert import RevertService
from app.simulator.clock import Clock

UowFactory = Callable[[], UnitOfWork]

# Only these can still be reverted; any other status shows the window closed (D011).
_REVERTIBLE = frozenset({TaskStatus.SCHEDULED, TaskStatus.EXECUTED})


@dataclass(frozen=True)
class TaskView:
    task: Task
    revert_open: bool | None  # None: the task never had a revert window
    revert_remaining: timedelta | None


@dataclass(frozen=True)
class SensorReadings:
    sensor: Sensor
    readings: tuple[Reading, ...]  # oldest first, at most `limit`


@dataclass(frozen=True)
class CycleView:
    cycle: CropCycle
    stages: tuple[Stage, ...]


class FarmQueries:
    def __init__(self, uow: UowFactory, clock: Clock, revert: RevertService) -> None:
        self._uow = uow
        self._clock = clock
        self._revert = revert

    def plots(self) -> Sequence[Plot]:
        with self._uow() as u:
            return u.plots.list()

    def zones(self, plot_id: int) -> Sequence[Zone]:
        with self._uow() as u:
            u.plots.get(plot_id)  # 404 for an unknown plot, not an empty list
            return u.zones.list_by_plot(plot_id)

    def readings(self, zone_id: int, limit: int) -> Sequence[SensorReadings]:
        with self._uow() as u:
            u.zones.get(zone_id)
            return [
                SensorReadings(sensor, tuple(u.readings.list_for_sensor(sensor.id)[-limit:]))
                for sensor in u.sensors.list_by_zone(zone_id)
                if sensor.id is not None
            ]

    def cycles(self) -> Sequence[CycleView]:
        with self._uow() as u:
            return [
                self._cycle_view(u, cycle)
                for plot in u.plots.list()
                if plot.id is not None
                for cycle in u.cycles.list_by_plot(plot.id)
            ]

    def cycle(self, cycle_id: int) -> CycleView:
        with self._uow() as u:
            return self._cycle_view(u, u.cycles.get(cycle_id))

    def tasks(self, status: TaskStatus | None = None) -> Sequence[TaskView]:
        with self._uow() as u:
            tasks = u.tasks.list(status=status)
        return [self.task_view(task) for task in tasks]

    def task_view(self, task: Task) -> TaskView:
        """The backend decides whether the revert window is open; the UI only shows it."""
        window = self._revert.window(task)
        if window is None:
            return TaskView(task, None, None)
        return TaskView(task, window.open and task.status in _REVERTIBLE, window.remaining)

    def events(self, task_id: int | None, kind: EventKind | None, limit: int) -> Sequence[Event]:
        with self._uow() as u:
            return u.events.list(task_id=task_id, kind=kind)[-limit:]

    def notifications(self, unread_only: bool) -> Sequence[Notification]:
        with self._uow() as u:
            return u.notifications.list(unread_only=unread_only)

    def mark_read(self, notification_id: int) -> Notification:
        with self._uow() as u:
            note = u.notifications.mark_read(notification_id, self._clock.now())
            u.commit()
        return note

    def reports(self) -> Sequence[Report]:
        with self._uow() as u:
            return [
                report
                for plot in u.plots.list()
                if plot.id is not None
                for cycle in u.cycles.list_by_plot(plot.id)
                if cycle.id is not None
                for report in u.reports.list_by_cycle(cycle.id)
            ]

    @staticmethod
    def _cycle_view(u: UnitOfWork, cycle: CropCycle) -> CycleView:
        stages = u.stages.list_by_cycle(cycle.id) if cycle.id is not None else []
        return CycleView(cycle, tuple(stages))
