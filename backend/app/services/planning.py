"""Stage 1 served: a planting plan per plot (architecture §4.11, D079, D081).

The plan is advice: it never creates, changes or proposes a task. Each plan
served is logged as one planting_plan_served event.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from fieldpilot_planner.crops import CropCard
from fieldpilot_planner.serving import IncompleteHistoryError, PlanOutputs, SowingContext

from app.domain.enums import EventKind
from app.domain.errors import MissingDataError
from app.domain.models import Event, JsonValue, PlanAtSowing, Plot
from app.persistence.ports import UnitOfWork
from app.phenology.catalog import CropCatalog
from app.planning.models import CropOutlook, PlantingPlan, SowingWeek
from app.planning.ports import CropRecommender, SiteRecord, SiteSource
from app.services.gate_context import local_day
from app.simulator.clock import Clock

UowFactory = Callable[[], UnitOfWork]
MAX_WEEKS = 12
RECOMMENDED_TOP = 3  # the top 3 of a week are "recommended" (NDCG@3, D079; D083)


@dataclass(frozen=True)
class SowingAdvice:
    plan: PlanAtSowing | None  # None: not a planner crop, or no site data
    top: tuple[str, ...]  # the week's recommended crops, Spanish names

    @property
    def recommended(self) -> bool:
        return self.plan is not None and self.plan.rank <= RECOMMENDED_TOP


@dataclass(frozen=True)
class PlanRequest:
    plot_id: int
    first_sowing: date | None  # None: the plot's current local day
    weeks: int
    actor: str


class PlanningService:
    def __init__(
        self,
        uow: UowFactory,
        clock: Clock,
        sites: SiteSource,
        recommender: CropRecommender,
        catalog: CropCatalog,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._sites = sites
        self._recommender = recommender
        self._catalog = catalog

    @property
    def model_id(self) -> str:
        return self._recommender.model_id

    def plan(self, request: PlanRequest) -> PlantingPlan:
        if not 1 <= request.weeks <= MAX_WEEKS:
            raise ValueError(f"weeks must be between 1 and {MAX_WEEKS}")
        now = self._clock.now()
        with self._uow() as uow:
            plot = uow.plots.get(request.plot_id)
        first = request.first_sowing or local_day(now, plot)
        dates = [first + timedelta(weeks=i) for i in range(request.weeks)]
        site, weeks = self._weeks(plot, dates)
        plan = PlantingPlan(request.plot_id, now, self.model_id, site.snapshot.built_on, weeks)
        self._log(plan, request, site.sha256)
        return plan

    def advice(self, plot: Plot, sowing_date: date, crop: str) -> SowingAdvice:
        """Where a crop ranks on a sowing date, for the sowing confirmation (D083).

        Not logged as a plan served: the farmer is confirming, not asking. Without
        site data the planner cannot judge, and says so instead of guessing.
        """
        try:
            _, weeks = self._weeks(plot, [sowing_date])
        except MissingDataError:
            return SowingAdvice(None, ())
        outlooks = weeks[0].outlooks
        top = tuple(o.name_es for o in outlooks[:RECOMMENDED_TOP])
        for rank, outlook in enumerate(outlooks, start=1):
            if outlook.crop == crop:
                plan = PlanAtSowing(self.model_id, rank, outlook.rel_yield_p50, outlook.p_success)
                return SowingAdvice(plan, top)
        return SowingAdvice(None, top)

    def _weeks(self, plot: Plot, dates: list[date]) -> tuple[SiteRecord, tuple[SowingWeek, ...]]:
        site = self._sites.site(plot)
        try:
            result = self._recommender.recommend(site.snapshot, dates)
        except IncompleteHistoryError as error:
            raise MissingDataError(str(error)) from error
        weeks = tuple(
            self._week(context, result.outputs, row) for row, context in enumerate(result.contexts)
        )
        return site, weeks

    def _week(self, context: SowingContext, outputs: PlanOutputs, row: int) -> SowingWeek:
        outlooks = [
            self._outlook(card, context.sowing_date, outputs, row, column)
            for column, card in enumerate(self._recommender.crops)
        ]
        outlooks.sort(key=lambda o: (-o.rel_yield_p50, -o.p_success, o.crop))
        return SowingWeek(
            sowing_date=context.sowing_date,
            weather_until=context.history_end,
            oni=round(context.oni, 2),
            oni_latest_published=context.oni_latest_published,
            outlooks=tuple(outlooks),
        )

    def _outlook(
        self, card: CropCard, sowing: date, outputs: PlanOutputs, row: int, column: int
    ) -> CropOutlook:
        p = outputs.predictions
        p10, p50, p90 = (float(v) for v in p.rel_yield[row, column])
        return CropOutlook(
            crop=card.crop,
            name_es=card.name_es,
            sowing_date=sowing,
            harvest_date=sowing + timedelta(days=card.cycle_days),
            rel_yield_p10=round(p10, 3),
            rel_yield_p50=round(p50, 3),
            rel_yield_p90=round(p90, 3),
            p_success=round(float(p.success[row, column]), 3),
            irrigation_mm_p50=round(float(p.irrigation_mm[row, column, 1]), 1),
            heat_days=round(float(outputs.heat_days[row, column]), 1),
            cold_days=round(float(outputs.cold_days[row, column]), 1),
            automatable=card.crop in self._catalog,
        )

    def _log(self, plan: PlantingPlan, request: PlanRequest, site_sha256: str) -> None:
        """One event per plan served: why a crop was sown on a date can be traced (D079)."""
        top: list[JsonValue] = [
            {
                "sowing_date": w.sowing_date.isoformat(),
                "crop": w.outlooks[0].crop,
                "rel_yield_p50": w.outlooks[0].rel_yield_p50,
            }
            for w in plan.weeks
        ]
        best = max(plan.weeks, key=lambda w: w.outlooks[0].rel_yield_p50)
        reason = (
            f"Plan de siembra servido ({plan.model}): mejor opción {best.outlooks[0].name_es} "
            f"sembrando el {best.sowing_date.isoformat()}."
        )
        with self._uow() as uow:
            uow.events.append(
                Event(
                    kind=EventKind.PLANTING_PLAN_SERVED,
                    actor=request.actor,
                    reason=reason,
                    occurred_at=plan.generated_at,
                    inputs={
                        "plot_id": plan.plot_id,
                        "model": plan.model,
                        "site_sha256": site_sha256,
                        "first_sowing": plan.weeks[0].sowing_date.isoformat(),
                        "weeks": len(plan.weeks),
                        "top_per_week": top,
                    },
                )
            )
            uow.commit()
