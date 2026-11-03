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


# What a finished job says, stored by key and shown in APP_LANGUAGE (D084).
SITE_MESSAGES = {
    "site_build_failed": "The plot's data (climate or soil) could not be downloaded. Try again.",
    "site_build_off": "Downloading site data is turned off on this server.",
    "site_build_interrupted": "A server restart interrupted it. Try again.",
}


class SiteBuildError(Exception):
    """The snapshot could not be built; `key` is one of SITE_MESSAGES."""

    def __init__(self, key: str = "site_build_failed") -> None:
        super().__init__(SITE_MESSAGES[key])
        self.key = key


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
            raise SiteBuildError() from error
        if result.returncode != 0 or not partial.is_file():
            raise SiteBuildError()
        partial.replace(out)


class DisabledSiteBuilder:
    """PLANNER_SITE_BUILDER=off: CI and tests never reach the network."""

    def build(self, *args: object, **kwargs: object) -> None:
        raise SiteBuildError("site_build_off")


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
                raise SiteJobPendingError(
                    "This plot's data is already being prepared.", key="site_job_pending"
                )
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
                            "site_build_interrupted")
                )  # fmt: skip
            uow.commit()

    def _run(self, plot: Plot, job: SiteJob) -> None:
        self._out_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._builder.build(plot.latitude, plot.longitude, self.path_for(job.plot_id))
        except SiteBuildError as error:
            finished = SiteJob(job.plot_id, SiteStatus.FAILED, job.requested_at, self._wall(),
                               error.key)  # fmt: skip
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
