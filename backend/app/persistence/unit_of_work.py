"""SQL unit of work: one session, one transaction, every repository."""

from types import TracebackType
from typing import Self

from sqlalchemy import Engine
from sqlmodel import Session

from app.persistence.repositories.crop import (
    SqlCropCycleRepository,
    SqlReportRepository,
    SqlStageRepository,
)
from app.persistence.repositories.events import SqlEventRepository
from app.persistence.repositories.field import (
    SqlPlotRepository,
    SqlReadingRepository,
    SqlSensorRepository,
    SqlZoneRepository,
)
from app.persistence.repositories.system import (
    SqlControlStateRepository,
    SqlNotificationRepository,
    SqlSimClockStateRepository,
)
from app.persistence.repositories.tasks import SqlDecisionRepository, SqlTaskRepository


class SqlUnitOfWork:
    """Context manager that rolls back anything not explicitly committed.

    Usage:
        with SqlUnitOfWork(engine) as uow:
            uow.tasks.transition(task_id, TaskStatus.EXECUTED, event)
            uow.commit()
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __enter__(self) -> Self:
        self._session = Session(self._engine)
        session = self._session
        self.events = SqlEventRepository(session)
        self.plots = SqlPlotRepository(session)
        self.zones = SqlZoneRepository(session)
        self.sensors = SqlSensorRepository(session)
        self.readings = SqlReadingRepository(session)
        self.cycles = SqlCropCycleRepository(session)
        self.stages = SqlStageRepository(session)
        self.tasks = SqlTaskRepository(session, self.events)
        self.decisions = SqlDecisionRepository(session)
        self.notifications = SqlNotificationRepository(session)
        self.reports = SqlReportRepository(session)
        self.control = SqlControlStateRepository(session, self.events)
        self.sim_clock = SqlSimClockStateRepository(session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        # After a commit this rollback is a no-op; otherwise it discards everything.
        self._session.rollback()
        self._session.close()

    def commit(self) -> None:
        """Commit every write made through this unit of work."""
        self._session.commit()
