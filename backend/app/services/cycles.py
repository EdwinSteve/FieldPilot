"""The sowing and the harvest the farmer confirms (architecture §4.13, §4.14, D083).

A plan is advice. A cycle starts only when the farmer says they sowed, and a
lot is born only when they say they harvested.
"""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import date, timedelta

from app.domain.enums import CycleStatus, EventKind, TaskStatus
from app.domain.errors import (
    ActiveCycleExistsError,
    InvalidHarvestError,
    InvalidSowingDateError,
    InvalidTransitionError,
    OpenTasksError,
    OwnRiskRequiredError,
)
from app.domain.models import CropCycle, Event, JsonValue, Plot
from app.identity.models import Principal
from app.market.trace.chain import link
from app.market.trace.models import GENESIS_HASH, BizStep, Grade, HarvestLot
from app.market.trace.record import cultivation, plan_record, source_digest, source_events
from app.persistence.ports import UnitOfWork
from app.phenology.catalog import CropCatalog
from app.services.gate_context import local_day
from app.services.planning import PlanningService
from app.simulator.clock import Clock

UowFactory = Callable[[], UnitOfWork]
MAX_BACKDATE_DAYS = 60
MAX_KG_PER_HA = 100_000  # above any crop in the catalogue: a typo, not a harvest
CROP_SLUG = re.compile(r"^[a-z][a-z_]{1,39}$")
_OPEN = frozenset({TaskStatus.PENDING_APPROVAL, TaskStatus.SCHEDULED})


@dataclass(frozen=True)
class NewCycle:
    crop: str
    sowing_date: date
    accept_own_risk: bool


@dataclass(frozen=True)
class Harvest:
    harvested_on: date
    quantity_kg: float
    grade: Grade


class CycleService:
    def __init__(
        self,
        uow: UowFactory,
        clock: Clock,
        planning: PlanningService,
        catalog: CropCatalog,
        crop_names: Mapping[str, str],
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._planning = planning
        self._catalog = catalog
        self._crop_names = crop_names

    def start(self, principal: Principal, plot_id: int, form: NewCycle) -> CropCycle:
        """The sowing confirmation: one active cycle per plot, a date that already happened."""
        if not CROP_SLUG.fullmatch(form.crop):
            raise InvalidSowingDateError(
                "El cultivo debe ser un nombre en minúsculas, sin espacios."
            )
        with self._uow() as uow:
            plot = uow.plots.get(plot_id)
            if any(c.status is CycleStatus.ACTIVE for c in uow.cycles.list_by_plot(plot_id)):
                raise ActiveCycleExistsError(
                    "La parcela ya tiene un ciclo activo. Cosecha primero."
                )
        today = local_day(self._clock.now(), plot)
        if not today - timedelta(days=MAX_BACKDATE_DAYS) <= form.sowing_date <= today:
            raise InvalidSowingDateError(
                "La siembra se confirma cuando ya ocurrió: "
                f"entre hace {MAX_BACKDATE_DAYS} días y hoy."
            )
        advice = self._planning.advice(plot, form.sowing_date, form.crop)
        if not advice.recommended and not form.accept_own_risk:
            raise OwnRiskRequiredError(self._risk_message(form.crop, advice.top))
        cycle = CropCycle(
            plot_id=plot_id,
            crop=form.crop,
            sowing_date=form.sowing_date,
            automated=form.crop in self._catalog,
            own_risk=not advice.recommended,
            plan=advice.plan,
        )
        with self._uow() as uow:
            stored = uow.cycles.add(cycle)
            uow.events.append(self._started_event(stored, principal))
            uow.commit()
        return stored

    def harvest(self, principal: Principal, cycle_id: int, form: Harvest) -> HarvestLot:
        """The harvest confirmation: the only way a lot is born (§4.14)."""
        now = self._clock.now()
        with self._uow() as uow:
            cycle = uow.cycles.get(cycle_id)
            plot = uow.plots.get(cycle.plot_id)
            self._check_harvest(cycle, plot, form, local_day(now, plot))
            tasks = uow.tasks.list(cycle_id=cycle_id)
            if any(t.status in _OPEN for t in tasks):
                raise OpenTasksError(
                    "Hay tareas pendientes o programadas en este ciclo. "
                    "Apruébalas o recházalas antes de cosechar."
                )
            events = uow.events.list()
            known = any(
                e.kind is EventKind.CYCLE_STARTED and e.inputs.get("cycle_id") == cycle_id
                for e in events
            )
            seq = uow.lots.count_on(plot.id or 0, form.harvested_on) + 1
            lot = HarvestLot(
                code=f"FP-{plot.id}-{form.harvested_on:%Y%m%d}-{seq}",
                cycle_id=cycle_id,
                plot_id=cycle.plot_id,
                crop=cycle.crop,
                harvested_on=form.harvested_on,
                quantity_g=round(form.quantity_kg * 1000),
                grade=form.grade,
                created_at=now,
            )
            sealed: dict[str, JsonValue] = {
                "source_digest": source_digest(source_events(cycle_id, tasks, events)),
                "sowing_date": cycle.sowing_date.isoformat(),
                "cultivation": cultivation(cycle, tasks),
                "plan": plan_record(cycle, known),
            }
            commissioning = link(lot.code, 0, BizStep.COMMISSIONING, now, principal.actor,
                                 lot.quantity_g, sealed, GENESIS_HASH)  # fmt: skip
            uow.cycles.update(
                replace(cycle, status=CycleStatus.COMPLETED, harvested_on=form.harvested_on)
            )
            stored = uow.lots.add(lot)
            uow.trace_events.append(commissioning)
            uow.events.append(self._harvest_event(lot, principal))
            uow.events.append(self._commissioned_event(lot, commissioning.hash, principal))
            uow.commit()
        return stored

    def _check_harvest(self, cycle: CropCycle, plot: Plot, form: Harvest, today: date) -> None:
        if cycle.status is not CycleStatus.ACTIVE:
            raise InvalidTransitionError("Este ciclo ya fue cosechado.")
        if not cycle.sowing_date < form.harvested_on <= today:
            raise InvalidHarvestError(
                "La fecha de cosecha debe ser posterior a la siembra y no puede ser futura."
            )
        if not 0 < form.quantity_kg <= MAX_KG_PER_HA * plot.area_ha:
            raise InvalidHarvestError(
                f"La cantidad debe ser mayor que 0 y como máximo {MAX_KG_PER_HA:,} kg por hectárea."
            )

    def _risk_message(self, crop: str, top: tuple[str, ...]) -> str:
        name = self._crop_names.get(crop, crop)
        if not top:
            return (
                f"El planificador no puede evaluar {name} en esta parcela todavía. "
                "Para sembrar, confirma que lo haces bajo tu propio riesgo."
            )
        return (
            f"{name} no está entre los recomendados para esa semana ({', '.join(top)}). "
            "Para sembrarlo, confirma que lo haces bajo tu propio riesgo."
        )

    def _started_event(self, cycle: CropCycle, principal: Principal) -> Event:
        plan = cycle.plan
        mode = "automatizado" if cycle.automated else "manual"
        choice = "bajo su propio riesgo" if cycle.own_risk else "según la recomendación"
        return Event(
            kind=EventKind.CYCLE_STARTED,
            actor=principal.actor,
            reason=f"Siembra confirmada: {cycle.crop} el {cycle.sowing_date}, {mode}, {choice}.",
            occurred_at=self._clock.now(),
            inputs={
                "cycle_id": cycle.id,
                "plot_id": cycle.plot_id,
                "crop": cycle.crop,
                "sowing_date": cycle.sowing_date.isoformat(),
                "automated": cycle.automated,
                "own_risk": cycle.own_risk,
                "plan_model": None if plan is None else plan.model,
                "plan_rank": None if plan is None else plan.rank,
                "plan_rel_yield_p50": None if plan is None else plan.rel_yield_p50,
                "plan_p_success": None if plan is None else plan.p_success,
            },
        )

    def _harvest_event(self, lot: HarvestLot, principal: Principal) -> Event:
        return Event(
            kind=EventKind.HARVEST_CONFIRMED,
            actor=principal.actor,
            reason=f"Cosecha confirmada: {lot.quantity_kg:g} kg de {lot.crop} ({lot.grade}).",
            occurred_at=lot.created_at,
            inputs={
                "cycle_id": lot.cycle_id,
                "lot_code": lot.code,
                "harvested_on": lot.harvested_on.isoformat(),
                "quantity_g": lot.quantity_g,
                "grade": lot.grade.value,
            },
        )

    def _commissioned_event(self, lot: HarvestLot, head: str, principal: Principal) -> Event:
        return Event(
            kind=EventKind.LOT_COMMISSIONED,
            actor=principal.actor,
            reason=f"Lote {lot.code} creado con su pasaporte.",
            occurred_at=lot.created_at,
            inputs={"lot_code": lot.code, "cycle_id": lot.cycle_id, "chain_head": head},
        )
