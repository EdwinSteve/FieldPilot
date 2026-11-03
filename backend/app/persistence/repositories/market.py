"""Repositories for plot site jobs, harvest lots and their trace (§4.13, §4.14, D083)."""

from collections.abc import Sequence
from datetime import date

from sqlmodel import Session, col, func, select

from app.domain.errors import NotFoundError
from app.market.trace.models import BizStep, Grade, HarvestLot, TraceEvent
from app.persistence.repositories._base import insert
from app.persistence.tables import HarvestLotRow, PlotSiteRow, TraceEventRow
from app.planning.models import SiteJob, SiteStatus


class SqlPlotSiteRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, plot_id: int) -> SiteJob | None:
        row = self._session.get(PlotSiteRow, plot_id)
        return None if row is None else _job(row)

    def save(self, job: SiteJob) -> None:
        row = self._session.get(PlotSiteRow, job.plot_id) or PlotSiteRow(
            plot_id=job.plot_id, status=job.status.value, requested_at=job.requested_at
        )
        row.status, row.requested_at = job.status.value, job.requested_at
        row.finished_at, row.message = job.finished_at, job.message
        self._session.add(row)
        self._session.flush()

    def pending(self) -> Sequence[SiteJob]:
        query = select(PlotSiteRow).where(PlotSiteRow.status == SiteStatus.PENDING.value)
        return [_job(row) for row in self._session.exec(query)]


def _job(row: PlotSiteRow) -> SiteJob:
    return SiteJob(row.plot_id, SiteStatus(row.status), row.requested_at, row.finished_at,
                   row.message)  # fmt: skip


class SqlHarvestLotRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, lot: HarvestLot) -> HarvestLot:
        return _lot(insert(self._session, _lot_row(lot)))

    def get(self, code: str) -> HarvestLot:
        row = self._session.get(HarvestLotRow, code)
        if row is None:
            raise NotFoundError("Lot", code)
        return _lot(row)

    def find_by_cycle(self, cycle_id: int) -> HarvestLot | None:
        row = self._session.exec(
            select(HarvestLotRow).where(HarvestLotRow.cycle_id == cycle_id)
        ).first()
        return None if row is None else _lot(row)

    def list_by_plot(self, plot_id: int) -> Sequence[HarvestLot]:
        query = (
            select(HarvestLotRow)
            .where(HarvestLotRow.plot_id == plot_id)
            .order_by(col(HarvestLotRow.created_at))
        )
        return [_lot(row) for row in self._session.exec(query)]

    def count_on(self, plot_id: int, harvested_on: date) -> int:
        query = select(func.count()).where(
            HarvestLotRow.plot_id == plot_id, HarvestLotRow.harvested_on == harvested_on
        )
        return int(self._session.exec(query).one())


class SqlTraceEventRepository:
    """Append-only: there is deliberately no update or delete."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def append(self, event: TraceEvent) -> TraceEvent:
        return _trace(insert(self._session, _trace_row(event)))

    def list(self, lot_code: str) -> Sequence[TraceEvent]:
        query = (
            select(TraceEventRow)
            .where(TraceEventRow.lot_code == lot_code)
            .order_by(col(TraceEventRow.seq))
        )
        return [_trace(row) for row in self._session.exec(query)]


def _lot_row(lot: HarvestLot) -> HarvestLotRow:
    return HarvestLotRow(
        code=lot.code,
        cycle_id=lot.cycle_id,
        plot_id=lot.plot_id,
        crop=lot.crop,
        harvested_on=lot.harvested_on,
        quantity_g=lot.quantity_g,
        grade=lot.grade.value,
        created_at=lot.created_at,
    )


def _lot(row: HarvestLotRow) -> HarvestLot:
    return HarvestLot(
        code=row.code,
        cycle_id=row.cycle_id,
        plot_id=row.plot_id,
        crop=row.crop,
        harvested_on=row.harvested_on,
        quantity_g=row.quantity_g,
        grade=Grade(row.grade),
        created_at=row.created_at,
    )


def _trace_row(event: TraceEvent) -> TraceEventRow:
    return TraceEventRow(
        id=event.id,
        lot_code=event.lot_code,
        seq=event.seq,
        biz_step=event.biz_step.value,
        occurred_at=event.occurred_at,
        actor=event.actor,
        quantity_g=event.quantity_g,
        data=dict(event.data),
        prev_hash=event.prev_hash,
        hash=event.hash,
    )


def _trace(row: TraceEventRow) -> TraceEvent:
    return TraceEvent(
        id=row.id,
        lot_code=row.lot_code,
        seq=row.seq,
        biz_step=BizStep(row.biz_step),
        occurred_at=row.occurred_at,
        actor=row.actor,
        quantity_g=row.quantity_g,
        data=row.data,
        prev_hash=row.prev_hash,
        hash=row.hash,
    )
