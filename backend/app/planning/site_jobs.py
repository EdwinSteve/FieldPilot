"""Build a plot's site snapshot in the background (§4.13, D083).

The planner's own environment does the work in a subprocess, so GDAL and
rasterio never enter the backend. One build runs at a time; its state is
stored, so the API can answer while it runs and after a restart.
"""

import subprocess
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Protocol

from app.domain.errors import SiteJobPendingError
from app.domain.models import Plot
from app.persistence.ports import UnitOfWork
from app.planning.models import SiteJob, SiteStatus
from app.simulator.clock import WallClock

UowFactory = Callable[[], UnitOfWork]
Runner = Callable[[Callable[[], None]], None]
BUILD_TIMEOUT_S = 900  # NASA POWER from 1991 and the SoilGrids rasters: about 1 to 3 minutes


class SiteBuildError(Exception):
    """The snapshot could not be built; the message is safe to show."""


class SiteBuilder(Protocol):
    def build(self, lat: float, lon: float, out: Path) -> None: ...


class SubprocessSiteBuilder:
    """Runs `fieldpilot_planner.site` with the planner's `data` extra (make planner-site)."""

    def __init__(self, planner_dir: Path) -> None:
        self._planner_dir = planner_dir

    def build(self, lat: float, lon: float, out: Path) -> None:
        partial = out.with_suffix(".part")  # never leave a half-written snapshot behind
        command = [
            "uv", "run", "--directory", str(self._planner_dir), "--extra", "data",
            "python", "-m", "fieldpilot_planner.site",
            "--lat", f"{lat:.5f}", "--lon", f"{lon:.5f}", "--out", str(partial.resolve()),
        ]  # fmt: skip
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=BUILD_TIMEOUT_S, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise SiteBuildError("No se pudo descargar los datos de la parcela.") from error
        if result.returncode != 0 or not partial.is_file():
            raise SiteBuildError(
                "No se pudo descargar los datos de la parcela (clima o suelo). Intenta de nuevo."
            )
        partial.replace(out)


class DisabledSiteBuilder:
    """PLANNER_SITE_BUILDER=off: CI and tests never reach the network."""

    def build(self, *args: object, **kwargs: object) -> None:
        raise SiteBuildError("La descarga de datos de sitio está desactivada en este servidor.")


class SiteJobs:
    def __init__(
        self,
        uow: UowFactory,
        wall: WallClock,
        builder: SiteBuilder,
        out_dir: Path,
        runner: Runner | None = None,
    ) -> None:
        self._uow = uow
        self._wall = wall
        self._builder = builder
        self._out_dir = out_dir
        self._runner = runner or _background()

    def path_for(self, plot_id: int) -> Path:
        return self._out_dir / f"site_{plot_id}.json"

    def start(self, plot: Plot) -> SiteJob:
        """Queue a build. A build already pending for the plot is a 409."""
        plot_id = _stored(plot)
        with self._uow() as uow:
            current = uow.plot_sites.get(plot_id)
            if current is not None and current.status is SiteStatus.PENDING:
                raise SiteJobPendingError("Los datos de esta parcela ya se están preparando.")
            job = SiteJob(plot_id, SiteStatus.PENDING, self._wall())
            uow.plot_sites.save(job)
            uow.commit()
        self._runner(lambda: self._run(plot, job))
        return job

    def recover(self) -> None:
        """A build still pending at startup was cut by a restart: say so, never wait forever."""
        with self._uow() as uow:
            for job in uow.plot_sites.pending():
                uow.plot_sites.save(
                    SiteJob(job.plot_id, SiteStatus.FAILED, job.requested_at, self._wall(),
                            "Se interrumpió por un reinicio del servidor. Intenta de nuevo.")
                )  # fmt: skip
            uow.commit()

    def _run(self, plot: Plot, job: SiteJob) -> None:
        self._out_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._builder.build(plot.latitude, plot.longitude, self.path_for(job.plot_id))
        except SiteBuildError as error:
            finished = SiteJob(job.plot_id, SiteStatus.FAILED, job.requested_at, self._wall(),
                               str(error))  # fmt: skip
        else:
            finished = SiteJob(job.plot_id, SiteStatus.READY, job.requested_at, self._wall())
        with self._uow() as uow:
            uow.plot_sites.save(finished)
            uow.commit()


def _background() -> Runner:
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="site-snapshot")

    def run(task: Callable[[], None]) -> None:
        executor.submit(task)

    return run


def _stored(plot: Plot) -> int:
    if plot.id is None:
        raise ValueError("plot was not stored")
    return plot.id
