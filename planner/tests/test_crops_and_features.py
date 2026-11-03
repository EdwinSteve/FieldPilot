from datetime import date
from pathlib import Path

import numpy as np
import pytest

from fieldpilot_planner.clean.climatology import leave_one_out, moving_mean
from fieldpilot_planner.clean.quality import fill_short_gaps
from fieldpilot_planner.clean.soil import total_available_water_mm
from fieldpilot_planner.config import YearSpan
from fieldpilot_planner.crops import MAX_CYCLE_DAYS, load_crops, midpoint

CROPS = Path(__file__).resolve().parent.parent / "configs" / "crops.yaml"


def test_every_crop_card_loads_and_its_kc_curve_spans_the_cycle() -> None:
    cards = load_crops(CROPS)
    assert {c.crop for c in cards} >= {"maize", "common_bean", "potato"}
    for card in cards:
        curve = card.kc_curve()
        assert len(curve) == card.cycle_days <= MAX_CYCLE_DAYS
        assert curve[0] == pytest.approx(card.kc_ini)
        assert curve[-1] == pytest.approx(card.kc_end)


def test_ranges_use_their_midpoint() -> None:
    assert midpoint([1.0, 1.7]) == pytest.approx(1.35)
    assert midpoint(0.55) == 0.55


def test_short_gaps_are_filled_long_ones_stay() -> None:
    series = np.array([1.0, np.nan, 3.0, np.nan, np.nan, np.nan, np.nan, 8.0])
    assert fill_short_gaps(series, max_gap=3) == 1
    assert series[1] == 2.0
    assert np.isnan(series[3:7]).all()


def test_taw_from_water_retention() -> None:
    profile = np.zeros((6, 7))
    profile[:, 5], profile[:, 6] = 32.0, 12.0  # θ33 and θ1500 in % volume
    assert total_available_water_mm(profile, 1.0) == pytest.approx(200.0)


def test_climatology_leaves_the_labelled_year_out() -> None:
    days = (date(1994, 1, 1) - date(1991, 1, 1)).days
    t = np.zeros(days)
    t[(date(1993, 1, 1) - date(1991, 1, 1)).days :] = 30.0  # only 1993 is hot
    clim = leave_one_out(
        t, t, t, t, t, date(1991, 1, 1), YearSpan(1991, 1993), range(1993, 1994), 1
    )
    assert np.allclose(clim[0, :365, 0], 0.0)  # 1993's own heat is not in its climatology
    assert np.allclose(moving_mean(np.array([1.0, np.nan, 3.0]), 3), [1.0, 2.0, 3.0])
