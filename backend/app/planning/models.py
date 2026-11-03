"""What a planting plan says, per crop and sowing week."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


@dataclass(frozen=True)
class CropOutlook:
    """One crop sown on one date, rainfed, as the planner sees it."""

    crop: str
    name: str  # in APP_LANGUAGE (D084)
    name_es: str  # always Spanish, kept for clients that read it
    sowing_date: date
    harvest_date: date
    rel_yield_p10: float  # fraction of the crop's potential yield
    rel_yield_p50: float
    rel_yield_p90: float
    p_success: float  # P(relative yield >= the success threshold)
    irrigation_mm_p50: float  # water the crop would need on top of rain
    heat_days: float
    cold_days: float
    automatable: bool  # the crop has a YAML in config/crops/: stage 2 can run it


@dataclass(frozen=True)
class SowingWeek:
    sowing_date: date
    weather_until: date  # the last day of real weather the planner read
    oni: float
    oni_latest_published: bool  # the season due before sowing was not out yet (D081)
    outlooks: tuple[CropOutlook, ...]  # best first: rel_yield_p50, then p_success


@dataclass(frozen=True)
class PlantingPlan:
    plot_id: int
    generated_at: datetime
    model: str  # the bundle id, or "b0-climatology"
    site_built_on: date
    weeks: tuple[SowingWeek, ...]


class SiteStatus(StrEnum):
    MISSING = "missing"  # no snapshot and no job (D083)
    PENDING = "pending"
    READY = "ready"  # read from the snapshot file, never stored
    FAILED = "failed"


@dataclass(frozen=True)
class SiteJob:
    """The last snapshot job of a plot."""

    plot_id: int
    status: SiteStatus  # pending or failed; a finished job leaves the file behind
    requested_at: datetime
    finished_at: datetime | None = None
    message: str | None = None  # a key of site_jobs.SITE_MESSAGES


@dataclass(frozen=True)
class SiteState:
    """What the plot's site data looks like now, for GET /plots/{id}/site."""

    status: SiteStatus
    requested_at: datetime | None
    finished_at: datetime | None
    message: str | None
    weather_until: date | None
    built_on: date | None
