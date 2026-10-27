"""Repositories for crop cycles, stages and reports."""

from collections.abc import Sequence

from sqlmodel import Session, col, select

from app.domain.models import CropCycle, Report, Stage
from app.persistence import mappers
from app.persistence.repositories._base import get_row_or_raise, insert
from app.persistence.tables import CropCycleRow, ReportRow, StageRow


class SqlCropCycleRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, cycle: CropCycle) -> CropCycle:
        return mappers.cycle_from_row(insert(self._session, mappers.cycle_to_row(cycle)))

    def get(self, cycle_id: int) -> CropCycle:
        row = get_row_or_raise(self._session, CropCycleRow, cycle_id, "CropCycle")
        return mappers.cycle_from_row(row)

    def list_by_plot(self, plot_id: int) -> Sequence[CropCycle]:
        query = (
            select(CropCycleRow)
            .where(CropCycleRow.plot_id == plot_id)
            .order_by(col(CropCycleRow.id))
        )
        return [mappers.cycle_from_row(row) for row in self._session.exec(query)]

    def update(self, cycle: CropCycle) -> CropCycle:
        if cycle.id is None:
            raise ValueError("cannot update a cycle that was never stored")
        row = get_row_or_raise(self._session, CropCycleRow, cycle.id, "CropCycle")
        row.accumulated_gdd = cycle.accumulated_gdd
        row.gdd_updated_through = cycle.gdd_updated_through
        row.status = cycle.status
        self._session.flush()
        return mappers.cycle_from_row(row)


class SqlStageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, stage: Stage) -> Stage:
        return mappers.stage_from_row(insert(self._session, mappers.stage_to_row(stage)))

    def update(self, stage: Stage) -> Stage:
        if stage.id is None:
            raise ValueError("cannot update a stage that was never stored")
        row = get_row_or_raise(self._session, StageRow, stage.id, "Stage")
        row.ended_at = stage.ended_at
        self._session.flush()
        return mappers.stage_from_row(row)

    def list_by_cycle(self, cycle_id: int) -> Sequence[Stage]:
        query = select(StageRow).where(StageRow.cycle_id == cycle_id).order_by(col(StageRow.id))
        return [mappers.stage_from_row(row) for row in self._session.exec(query)]


class SqlReportRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, report: Report) -> Report:
        return mappers.report_from_row(insert(self._session, mappers.report_to_row(report)))

    def get(self, report_id: int) -> Report:
        row = get_row_or_raise(self._session, ReportRow, report_id, "Report")
        return mappers.report_from_row(row)

    def list_by_cycle(self, cycle_id: int) -> Sequence[Report]:
        query = select(ReportRow).where(ReportRow.cycle_id == cycle_id).order_by(col(ReportRow.id))
        return [mappers.report_from_row(row) for row in self._session.exec(query)]
