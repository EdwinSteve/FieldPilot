"""Read-only views for the API: what the dashboard shows, from stored facts only."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from app.agent.field import ImageryReader, ImageryView
from app.autonomy.messages import MessageCatalog
from app.domain.enums import EventKind, TaskStatus
from app.domain.errors import NotFoundError
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
from app.market.trace.models import HarvestLot
from app.persistence.ports import UnitOfWork
from app.phenology.catalog import CropCatalog, CropSpec
from app.services.gate_context import local_day
from app.services.gate_decisions import verdict_from_event
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
    reason: str | None = None  # why it is held, in APP_LANGUAGE (D067, D084)
    reason_es: str | None = None  # the same, always in Spanish (kept for clients)


@dataclass(frozen=True)
class SensorReadings:
    sensor: Sensor
    readings: tuple[Reading, ...]  # oldest first, at most `limit`


@dataclass(frozen=True)
class CycleView:
    cycle: CropCycle
    stages: tuple[Stage, ...]
    lot_code: str | None = None  # set once the harvest was confirmed (D083)


class FarmQueries:
    def __init__(
        self,
        uow: UowFactory,
        clock: Clock,
        revert: RevertService,
        messages: MessageCatalog,
        imagery: ImageryReader,
        crops: CropCatalog,
        messages_es: MessageCatalog | None = None,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._revert = revert
        self._messages = messages  # APP_LANGUAGE
        self._messages_es = messages_es or messages  # the API's `_es` fields (D084)
        self._imagery = imagery
        self._crops = crops

    def plots(self) -> Sequence[Plot]:
        with self._uow() as u:
            return u.plots.list()

    def lots(self, plot_id: int) -> Sequence[HarvestLot]:
        with self._uow() as u:
            u.plots.get(plot_id)  # 404 for an unknown plot, not an empty list
            return u.lots.list_by_plot(plot_id)

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
        reason = self._held_reason(task, self._messages)
        reason_es = self._held_reason(task, self._messages_es)
        window = self._revert.window(task)
        if window is None:
            return TaskView(task, None, None, reason, reason_es)
        open_now = window.open and task.status in _REVERTIBLE
        return TaskView(task, open_now, window.remaining, reason, reason_es)

    def crop(self, name: str) -> CropSpec:
        """A crop of the catalogue, for the dashboard's stage bar (D077)."""
        if name not in self._crops:
            raise NotFoundError("Crop", name)
        return self._crops[name]

    def local_day(self, plot_id: int) -> date:
        """The plot's current calendar day, on the simulated clock (D018)."""
        with self._uow() as u:
            plot = u.plots.get(plot_id)
        return local_day(self._clock.now(), plot)

    def imagery(self, plot_id: int) -> ImageryView | None:
        """The plot's latest scene, on its current local day (D067)."""
        return self._imagery.imagery(plot_id, self.local_day(plot_id))

    def imagery_image(self, plot_id: int) -> bytes:
        """The plot's latest scene as PNG bytes, for the dashboard overlay (D073)."""
        png = self._imagery.scene_png(plot_id, self.local_day(plot_id))
        if png is None:
            raise NotFoundError("scene", plot_id)
        return png

    def _held_reason(self, task: Task, messages: MessageCatalog) -> str | None:
        """The stored verdict's rules, rendered from the catalogue (D067)."""
        if task.status is not TaskStatus.PENDING_APPROVAL or task.id is None:
            return None
        with self._uow() as u:
            verdicts = u.events.list(task_id=task.id, kind=EventKind.GATE_VERDICT)
        if not verdicts:
            return None
        violations = verdict_from_event(verdicts[-1]).violations
        return "; ".join(messages.render(v) for v in violations) or None

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
        if cycle.id is None:
            return CycleView(cycle, ())
        lot = u.lots.find_by_cycle(cycle.id)
        return CycleView(
            cycle, tuple(u.stages.list_by_cycle(cycle.id)), None if lot is None else lot.code
        )
