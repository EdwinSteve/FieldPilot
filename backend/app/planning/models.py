"""What a planting plan says, per crop and sowing week."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class CropOutlook:
    """One crop sown on one date, rainfed, as the planner sees it."""

    crop: str
    name_es: str
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
