"""Daily phenology update: degree-days from measured temperatures, stage transitions."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

from app.domain.enums import EventKind, SensorKind
from app.domain.errors import DayNotFinishedError, MissingDataError
from app.domain.models import CropCycle, Event, Stage
from app.persistence.ports import UnitOfWork
from app.phenology.catalog import CropCatalog, CropSpec, StageSpec
from app.phenology.gdd import daily_gdd, local_day_window, stage_for, transitions_between
from app.simulator.clock import Clock

UowFactory = Callable[[], UnitOfWork]
ACTOR = "system:phenology"


@dataclass(frozen=True)
class PhenologyUpdate:
    day: date
    already_processed: bool
    gdd_added: float = 0.0
    accumulated_gdd: float = 0.0
    entered_stages: tuple[str, ...] = ()
    gap_days: tuple[date, ...] = ()


class PhenologyService:
    def __init__(self, uow: UowFactory, catalog: CropCatalog, clock: Clock) -> None:
        self._uow = uow
        self._catalog = catalog
        self._clock = clock

    def update_cycle(self, cycle_id: int, day: date) -> PhenologyUpdate:
        """Count the GDD of one finished local day and record any stage change.

        Idempotent: a day at or before the last counted day changes nothing.
        A day without temperature readings raises `MissingDataError` and
        writes nothing; skipped days are recorded as a gap, never filled (D019).
        """
        with self._uow() as u:
            cycle = u.cycles.get(cycle_id)
            if cycle.gdd_updated_through is not None and day <= cycle.gdd_updated_through:
                return PhenologyUpdate(day, already_processed=True)
            if day < cycle.sowing_date:
                raise ValueError(f"{day} is before the sowing date {cycle.sowing_date}")

            plot = u.plots.get(cycle.plot_id)
            start, end = local_day_window(day, plot.utc_offset_hours)
            if end > self._clock.now():
                raise DayNotFinishedError(f"local day {day} has not ended yet")
            temperatures = _temperatures(u, cycle.plot_id, start, end)
            if not temperatures:
                raise MissingDataError(f"no temperature readings for local day {day}")

            crop = self._catalog[cycle.crop]
            t_min, t_max = min(temperatures), max(temperatures)
            gdd_added = daily_gdd(t_min, t_max, crop)
            accumulated = cycle.accumulated_gdd + gdd_added
            gaps = _gap_days(cycle, day)

            self._ensure_current_stage(u, cycle, crop, plot.utc_offset_hours)
            if gaps:
                u.events.append(self._gap_event(cycle_id, gaps))
            entered = transitions_between(cycle.accumulated_gdd, accumulated, crop)
            for stage in entered:
                self._enter_stage(u, cycle_id, stage, end, day, cycle.accumulated_gdd, accumulated)

            u.cycles.update(replace(cycle, accumulated_gdd=accumulated, gdd_updated_through=day))
            u.commit()

        return PhenologyUpdate(
            day=day,
            already_processed=False,
            gdd_added=gdd_added,
            accumulated_gdd=accumulated,
            entered_stages=tuple(stage.name for stage in entered),
            gap_days=gaps,
        )

    def _ensure_current_stage(
        self, u: UnitOfWork, cycle: CropCycle, crop: CropSpec, utc_offset_hours: float
    ) -> None:
        """Open the stage matching the accumulated GDD if the cycle has none yet."""
        if cycle.id is None or u.stages.list_by_cycle(cycle.id):
            return
        stage = stage_for(cycle.accumulated_gdd, crop)
        sowing_start, _ = local_day_window(cycle.sowing_date, utc_offset_hours)
        u.stages.add(Stage(cycle.id, stage.name, sowing_start, gdd_at_start=stage.gdd_start))

    def _enter_stage(
        self,
        u: UnitOfWork,
        cycle_id: int,
        stage: StageSpec,
        at: datetime,
        day: date,
        gdd_before: float,
        gdd_after: float,
    ) -> None:
        stages = u.stages.list_by_cycle(cycle_id)
        previous = next((s for s in reversed(stages) if s.ended_at is None), None)
        if previous is not None:
            u.stages.update(replace(previous, ended_at=at))
        u.stages.add(Stage(cycle_id, stage.name, started_at=at, gdd_at_start=stage.gdd_start))
        u.events.append(
            Event(
                kind=EventKind.STAGE_TRANSITION,
                actor=ACTOR,
                reason=(
                    f"Crop entered '{stage.name}': accumulated GDD reached "
                    f"{gdd_after:.1f} (threshold {stage.gdd_start:.1f}) on {day}."
                ),
                occurred_at=self._clock.now(),
                inputs={
                    "cycle_id": cycle_id,
                    "from_stage": previous.name if previous else None,
                    "to_stage": stage.name,
                    "day": day.isoformat(),
                    "gdd_before": gdd_before,
                    "gdd_after": gdd_after,
                    "threshold": stage.gdd_start,
                },
            )
        )

    def _gap_event(self, cycle_id: int, gaps: tuple[date, ...]) -> Event:
        return Event(
            kind=EventKind.PHENOLOGY_GAP,
            actor=ACTOR,
            reason=(
                f"No temperature data for {len(gaps)} day(s); their degree-days were not "
                "counted, so stage dates may lag behind the real crop."
            ),
            occurred_at=self._clock.now(),
            inputs={"cycle_id": cycle_id, "missing_days": [d.isoformat() for d in gaps]},
        )


def _gap_days(cycle: CropCycle, day: date) -> tuple[date, ...]:
    """Days between the last counted day (or sowing) and `day` that were never counted."""
    if cycle.gdd_updated_through is None:
        first_expected = cycle.sowing_date
    else:
        first_expected = cycle.gdd_updated_through + timedelta(days=1)
    count = (day - first_expected).days
    return tuple(first_expected + timedelta(days=i) for i in range(count))


def _temperatures(u: UnitOfWork, plot_id: int, start: datetime, end: datetime) -> Sequence[float]:
    values: list[float] = []
    for zone in u.zones.list_by_plot(plot_id):
        if zone.id is None:
            continue
        for sensor in u.sensors.list_by_zone(zone.id):
            if sensor.kind is SensorKind.TEMPERATURE and sensor.id is not None:
                values += [r.value for r in u.readings.list_for_sensor(sensor.id, start, end)]
    return values
