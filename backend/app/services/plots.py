"""Plots a farmer creates, and the state of their site data (architecture §4.13, D083)."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.autonomy.messages import MessageCatalog
from app.domain.errors import MissingDataError
from app.domain.models import Plot
from app.identity.models import Principal
from app.persistence.ports import UnitOfWork
from app.planning.models import SiteState, SiteStatus
from app.planning.ports import SiteSource
from app.planning.site_jobs import SITE_MESSAGES, SiteJobs
from app.services.sensor_kit import FieldInstaller
from app.simulator.clock import Clock

UowFactory = Callable[[], UnitOfWork]
COLOMBIA_UTC_OFFSET_HOURS = -5.0  # no daylight saving


@dataclass(frozen=True)
class NewPlot:
    name: str
    municipality: str
    department: str
    latitude: float
    longitude: float
    area_ha: float


class PlotService:
    def __init__(
        self,
        uow: UowFactory,
        clock: Clock,
        sites: SiteSource,
        jobs: SiteJobs,
        messages: MessageCatalog,
        installer: FieldInstaller | None = None,  # the demo's sensor kit (D089)
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._sites = sites
        self._jobs = jobs
        self._messages = messages
        self._installer = installer

    def create(self, principal: Principal, form: NewPlot) -> Plot:
        """Store the plot; its farmer becomes a member; its site data starts building. In
        the demo it also gets its simulated zones and sensors (D089)."""
        now = self._clock.now()
        with self._uow() as uow:
            plot = uow.plots.add(
                Plot(
                    name=form.name.strip(),
                    latitude=form.latitude,
                    longitude=form.longitude,
                    area_ha=form.area_ha,
                    created_at=now,
                    utc_offset_hours=COLOMBIA_UTC_OFFSET_HOURS,
                    municipality=form.municipality.strip(),
                    department=form.department.strip(),
                )
            )
            if plot.id is None:
                raise ValueError("plot was not stored")
            if principal.user_id is not None and not principal.sees_every_plot:
                uow.plot_members.add(plot.id, principal.user_id)
            if self._installer is not None:
                self._installer.install(uow, plot, now)
            uow.commit()
        self._jobs.start(plot)
        return plot

    def visible(self, principal: Principal) -> Sequence[Plot]:
        """A member's plots; an admin, and the demo farmer, see every plot."""
        with self._uow() as uow:
            plots = uow.plots.list()
            if principal.sees_every_plot or principal.user_id is None:
                return plots
            user_id = principal.user_id
            return [
                p for p in plots if p.id is not None and uow.plot_members.is_member(p.id, user_id)
            ]

    def site(self, plot_id: int) -> SiteState:
        with self._uow() as uow:
            plot = uow.plots.get(plot_id)
            job = uow.plot_sites.get(plot_id)
        try:
            snapshot = self._sites.site(plot).snapshot
        except MissingDataError:
            snapshot = None
        if snapshot is not None:
            return SiteState(
                SiteStatus.READY,
                None if job is None else job.requested_at,
                None if job is None else job.finished_at,
                None,
                snapshot.last_day,
                snapshot.built_on,
            )
        if job is None or job.status is SiteStatus.READY:  # no job, or its file is gone
            return SiteState(SiteStatus.MISSING, None, None, None, None, None)
        return SiteState(
            job.status, job.requested_at, job.finished_at, self._text(job.message), None, None
        )

    def _text(self, key: str | None) -> str | None:
        """A stored job message, in APP_LANGUAGE (D084)."""
        if key is None:
            return None
        return self._messages.error(key, {}, SITE_MESSAGES.get(key, key))

    def refresh_site(self, plot_id: int) -> SiteState:
        with self._uow() as uow:
            plot = uow.plots.get(plot_id)
        self._jobs.start(plot)
        return self.site(plot_id)
