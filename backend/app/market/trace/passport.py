"""The public passport of a lot: what was sealed at harvest, verified on every read (§4.14)."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta

from app.autonomy.messages import MessageCatalog
from app.domain.models import JsonValue
from app.market.trace.chain import verify_chain
from app.market.trace.models import TraceEvent
from app.market.trace.record import source_digest, source_events
from app.persistence.ports import UnitOfWork

UowFactory = Callable[[], UnitOfWork]
COLOMBIA_OFFSET = timedelta(hours=-5)  # the public sees local dates


@dataclass(frozen=True)
class Integrity:
    verified: bool  # the chain recomputes and the stage-2 log still gives the sealed digest
    chain_head: str
    source_digest: str
    trace_events: int


@dataclass(frozen=True)
class JourneyStep:
    """One step of the lot's chain, as the public may see it (D085)."""

    step: str  # commissioning | shipping | receiving | retail_selling
    on: date
    quantity_kg: float
    place: str | None  # the warehouse, when the step happened at one


@dataclass(frozen=True)
class Passport:
    """Never coordinates, names, phones, sensor readings or prices (market.md §4.2)."""

    lot_code: str
    crop: str
    crop_name: str  # in APP_LANGUAGE (D084)
    crop_name_es: str  # always Spanish, kept for clients that read it
    producer: str
    municipality: str
    department: str
    area_ha: float
    sowing_date: date
    harvested_on: date
    quantity_kg: float
    grade: str
    cultivation: Mapping[str, JsonValue]
    plan: Mapping[str, JsonValue]
    integrity: Integrity
    journey: tuple[JourneyStep, ...] = ()


class PassportService:
    def __init__(
        self, uow: UowFactory, messages: MessageCatalog, messages_es: MessageCatalog
    ) -> None:
        self._uow = uow
        self._messages = messages
        self._messages_es = messages_es

    def public(self, code: str) -> Passport:
        with self._uow() as uow:
            lot = uow.lots.get(code)
            chain = uow.trace_events.list(code)
            cycle = uow.cycles.get(lot.cycle_id)
            plot = uow.plots.get(lot.plot_id)
            tasks = uow.tasks.list(cycle_id=lot.cycle_id)
            events = uow.events.list()
        sealed = chain[0].data if chain else {}
        sealed_digest = str(sealed.get("source_digest", ""))
        current = source_digest(source_events(lot.cycle_id, tasks, events))
        place = ", ".join(p for p in (plot.municipality, plot.department) if p)
        return Passport(
            lot_code=lot.code,
            crop=lot.crop,
            crop_name=self._messages.crop_name(lot.crop),
            crop_name_es=self._messages_es.crop_name(lot.crop),
            producer=(
                self._messages.label("producer_of", place=place)
                if place
                else self._messages.label("producer_unknown")
            ),
            municipality=plot.municipality,
            department=plot.department,
            area_ha=plot.area_ha,
            sowing_date=cycle.sowing_date,
            harvested_on=lot.harvested_on,
            quantity_kg=lot.quantity_kg,
            grade=lot.grade.value,
            cultivation=_mapping(sealed.get("cultivation")),
            plan=_mapping(sealed.get("plan")),
            journey=tuple(_step(event) for event in chain),
            integrity=Integrity(
                verified=verify_chain(chain) and sealed_digest == current,
                chain_head=chain[-1].hash if chain else "",
                source_digest=sealed_digest,
                trace_events=len(chain),
            ),
        )


def _mapping(value: JsonValue | None) -> Mapping[str, JsonValue]:
    return value if isinstance(value, dict) else {}


def _step(event: TraceEvent) -> JourneyStep:
    place = event.data.get("warehouse_name")
    return JourneyStep(
        step=event.biz_step.value,
        on=(event.occurred_at + COLOMBIA_OFFSET).date(),
        quantity_kg=event.quantity_g / 1000,
        place=place if isinstance(place, str) else None,
    )
