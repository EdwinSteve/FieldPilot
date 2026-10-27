"""Degree-day and stage computations. Pure functions over `CropSpec`."""

import math
from collections.abc import Mapping
from datetime import UTC, date, datetime, time, timedelta

from app.phenology.catalog import CropSpec, StageSpec

MATURITY = "maturity"


def daily_gdd(t_min_c: float, t_max_c: float, crop: CropSpec) -> float:
    """Growing degree-days for one day, Modified 86/50 °F (10/30 °C) cutoff.

    Both the daily low and high are clamped to [base, upper] before
    averaging, so cold nights add no negative heat and heat waves are capped.
    """
    if t_min_c > t_max_c:
        raise ValueError(f"daily minimum {t_min_c} is above maximum {t_max_c}")
    low = _clamp(t_min_c, crop.base_temp_c, crop.upper_temp_c)
    high = _clamp(t_max_c, crop.base_temp_c, crop.upper_temp_c)
    return (low + high) / 2 - crop.base_temp_c


def stage_for(gdd: float, crop: CropSpec) -> StageSpec:
    """The stage in effect at `gdd`: the last one whose start is not after it."""
    if gdd < 0:
        raise ValueError("accumulated GDD cannot be negative")
    current = crop.stages[0]
    for stage in crop.stages:
        if stage.gdd_start <= gdd:
            current = stage
    return current


def transitions_between(
    gdd_before: float, gdd_after: float, crop: CropSpec
) -> tuple[StageSpec, ...]:
    """Stages entered when moving from `gdd_before` to `gdd_after` (may be several)."""
    if gdd_after < gdd_before:
        raise ValueError("accumulated GDD never decreases")
    return tuple(s for s in crop.stages if gdd_before < s.gdd_start <= gdd_after)


def crop_coefficient_at(gdd: float, crop: CropSpec) -> float:
    """Kc at `gdd`, linear within each stage (the FAO-56 Kc curve)."""
    stage = stage_for(gdd, crop)
    start, end = stage.gdd_start, crop.stage_end_gdd(stage)
    progress = min(max((gdd - start) / (end - start), 0.0), 1.0)
    return stage.kc_start + (stage.kc_end - stage.kc_start) * progress


def project_stage_dates(
    gdd: float, today: date, expected_daily_gdd: float, crop: CropSpec
) -> Mapping[str, date]:
    """Expected start date of every stage not yet reached, plus maturity.

    Hotter weather (higher `expected_daily_gdd`) brings the dates forward.
    A date is the first day by whose end the threshold is reached.
    """
    if expected_daily_gdd <= 0:
        raise ValueError("expected daily GDD must be positive")
    thresholds = {s.name: s.gdd_start for s in crop.stages if s.gdd_start > gdd}
    thresholds[MATURITY] = crop.maturity_gdd
    return {
        name: today + timedelta(days=math.ceil((threshold - gdd) / expected_daily_gdd))
        for name, threshold in thresholds.items()
        if threshold > gdd
    }


def local_day_window(day: date, utc_offset_hours: float) -> tuple[datetime, datetime]:
    """UTC bounds [start, end) of the plot's local calendar day (D018)."""
    local_midnight = datetime.combine(day, time(0), tzinfo=UTC)
    start = local_midnight - timedelta(hours=utc_offset_hours)
    return start, start + timedelta(days=1)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))
