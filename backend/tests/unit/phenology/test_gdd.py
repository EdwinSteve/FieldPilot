from datetime import UTC, date, datetime

import pytest

from app.phenology.catalog import CropSpec
from app.phenology.gdd import (
    MATURITY,
    crop_coefficient_at,
    daily_gdd,
    local_day_window,
    project_stage_dates,
    stage_for,
    transitions_between,
)

# --- daily GDD (10/30 °C cutoff) -------------------------------------------


@pytest.mark.parametrize(
    ("t_min", "t_max", "expected"),
    [
        (2.0, 9.0, 0.0),  # whole day below base: no heat, never negative
        (10.0, 10.0, 0.0),  # exactly at base
        (31.0, 38.0, 20.0),  # whole day above upper: capped
        (30.0, 30.0, 20.0),  # exactly at upper
        (5.0, 25.0, 7.5),  # low clamped up to 10
        (22.0, 34.0, 16.0),  # high clamped down to 30 (Neiva-like day)
        (15.0, 25.0, 10.0),  # no clamping
    ],
)
def test_daily_gdd_boundaries(t_min: float, t_max: float, expected: float, maize: CropSpec) -> None:
    assert daily_gdd(t_min, t_max, maize) == pytest.approx(expected)


def test_minimum_above_maximum_is_rejected(maize: CropSpec) -> None:
    with pytest.raises(ValueError, match="above maximum"):
        daily_gdd(25.0, 20.0, maize)


# --- stages ---------------------------------------------------------------


def test_stage_starts_exactly_at_its_threshold(maize: CropSpec) -> None:
    flowering = maize.stage("flowering")

    assert stage_for(flowering.gdd_start, maize) is flowering
    assert stage_for(flowering.gdd_start - 0.01, maize).name == "vegetative"


def test_zero_gdd_is_sowing(maize: CropSpec) -> None:
    assert stage_for(0.0, maize).name == "sowing"


def test_past_maturity_stays_in_the_last_stage(maize: CropSpec) -> None:
    assert stage_for(maize.maturity_gdd + 500, maize).name == "maturity_harvest"


def test_negative_gdd_is_rejected(maize: CropSpec) -> None:
    with pytest.raises(ValueError):
        stage_for(-1.0, maize)


def test_transitions_can_cross_several_stages(maize: CropSpec) -> None:
    entered = transitions_between(10.0, 800.0, maize)

    assert [s.name for s in entered] == ["germination_emergence", "vegetative", "flowering"]


def test_reaching_a_threshold_exactly_counts_once(maize: CropSpec) -> None:
    threshold = maize.stage("grain_fill").gdd_start

    assert [s.name for s in transitions_between(threshold - 5, threshold, maize)] == ["grain_fill"]
    assert transitions_between(threshold, threshold + 5, maize) == ()


def test_no_progress_means_no_transition(maize: CropSpec) -> None:
    assert transitions_between(300.0, 300.0, maize) == ()


def test_gdd_never_decreases(maize: CropSpec) -> None:
    with pytest.raises(ValueError, match="never decreases"):
        transitions_between(300.0, 200.0, maize)


# --- crop coefficient (FAO-56 curve) --------------------------------------


def test_kc_follows_the_fao56_curve(maize: CropSpec) -> None:
    vegetative = maize.stage("vegetative")
    midpoint = (vegetative.gdd_start + maize.stage("flowering").gdd_start) / 2

    assert crop_coefficient_at(0.0, maize) == pytest.approx(0.30)
    assert crop_coefficient_at(midpoint, maize) == pytest.approx(0.75)
    assert crop_coefficient_at(maize.stage("flowering").gdd_start, maize) == pytest.approx(1.20)
    assert crop_coefficient_at(maize.maturity_gdd, maize) == pytest.approx(0.60)
    assert crop_coefficient_at(maize.maturity_gdd + 100, maize) == pytest.approx(0.60)


STAGE_NAMES = [
    "sowing",
    "germination_emergence",
    "vegetative",
    "flowering",
    "grain_fill",
    "maturity_harvest",
]
EPSILON = 1e-6


@pytest.mark.parametrize("name", STAGE_NAMES)
def test_kc_equals_the_stage_extremes_on_its_first_and_last_day(maize: CropSpec, name: str) -> None:
    stage = maize.stage(name)
    end = maize.stage_end_gdd(stage)

    assert crop_coefficient_at(stage.gdd_start, maize) == pytest.approx(stage.kc_start)
    assert crop_coefficient_at(end - EPSILON, maize) == pytest.approx(stage.kc_end, abs=1e-6)


@pytest.mark.parametrize("boundary", STAGE_NAMES[1:])
def test_kc_has_no_jump_at_a_stage_change(maize: CropSpec, boundary: str) -> None:
    threshold = maize.stage(boundary).gdd_start

    just_before = crop_coefficient_at(threshold - EPSILON, maize)
    at_threshold = crop_coefficient_at(threshold, maize)

    assert at_threshold == pytest.approx(just_before, abs=1e-6)


# --- projections ----------------------------------------------------------

TODAY = date(2026, 10, 27)


def test_hotter_weather_brings_dates_forward(maize: CropSpec) -> None:
    cool = project_stage_dates(100.0, TODAY, expected_daily_gdd=10.0, crop=maize)
    hot = project_stage_dates(100.0, TODAY, expected_daily_gdd=16.0, crop=maize)

    assert hot["flowering"] < cool["flowering"]
    assert hot[MATURITY] < cool[MATURITY]


def test_projection_counts_whole_days(maize: CropSpec) -> None:
    dates = project_stage_dates(780.0, TODAY, expected_daily_gdd=10.0, crop=maize)

    assert dates["flowering"] == date(2026, 10, 28)  # 8.9 GDD short: reached by end of day 1
    assert "vegetative" not in dates  # already reached


def test_projection_requires_positive_rate(maize: CropSpec) -> None:
    with pytest.raises(ValueError):
        project_stage_dates(0.0, TODAY, expected_daily_gdd=0.0, crop=maize)


# --- local day (D018) -----------------------------------------------------


def test_local_day_window_for_utc_minus_5() -> None:
    start, end = local_day_window(date(2026, 10, 27), utc_offset_hours=-5.0)

    assert start == datetime(2026, 10, 27, 5, 0, tzinfo=UTC)
    assert end == datetime(2026, 10, 28, 5, 0, tzinfo=UTC)
