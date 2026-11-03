"""Serving a plot from its site snapshot (D081): the same features and oracle as training."""

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

from fieldpilot_planner.clean.climatology import (
    CLIM_OUTPUTS,
    DOY,
    leave_one_out,
    served_climatology,
)
from fieldpilot_planner.config import YearSpan
from fieldpilot_planner.crops import CROP_FEATURES, load_crops
from fieldpilot_planner.features import (
    AHEAD_DAYS,
    CLIM_CHANNELS,
    HISTORY_DAYS,
    STATIC_FEATURES,
    WEATHER_CHANNELS,
    Normalization,
    Standardizer,
)
from fieldpilot_planner.oracle.labels import LABELS
from fieldpilot_planner.serving import (
    IncompleteHistoryError,
    SiteSnapshot,
    climatology_plan,
    decode_b0,
    plan_inputs,
)
from fieldpilot_planner.sources.soilgrids import LAYER_BOUNDS_CM, PROPERTIES

CROPS = load_crops(Path(__file__).resolve().parents[1] / "configs" / "crops.yaml")
FIRST = date(2024, 11, 1)
DAYS = 730


def _snapshot(valid_days: int = DAYS) -> SiteSnapshot:
    rng = np.random.default_rng(3)
    weather = np.zeros((DAYS, len(WEATHER_CHANNELS)), dtype=np.float32)
    index = {c: i for i, c in enumerate(WEATHER_CHANNELS)}
    weather[:, index["t2m"]] = 26 + rng.normal(0, 1, DAYS)
    weather[:, index["rain"]] = rng.gamma(0.5, 6, DAYS)
    weather[:, index["et0"]] = 4.5
    clim = np.zeros((DOY, len(CLIM_OUTPUTS)), dtype=np.float32)
    for name, value in {"t_mean": 26, "rain_mean": 3, "tmax_mean": 32, "tmin_mean": 21,
                        "et0_mean": 4.5}.items():  # fmt: skip
        clim[:, CLIM_OUTPUTS.index(name)] = value
    soil = np.zeros((len(LAYER_BOUNDS_CM), len(PROPERTIES)), dtype=np.float32)
    soil[:, PROPERTIES.index("phh2o")] = 6.5
    soil[:, PROPERTIES.index("wv0033")] = 30
    soil[:, PROPERTIES.index("wv1500")] = 15
    valid = np.arange(DAYS) >= DAYS - valid_days
    oni = {(y, m): 0.5 for y in (2024, 2025, 2026) for m in range(1, 13) if (y, m) <= (2026, 9)}
    return SiteSnapshot(2.93, -75.28, 442.0, 500.0, soil, clim, FIRST, weather, valid, oni,
                        FIRST + timedelta(days=DAYS))  # fmt: skip


def _identity_norm() -> Normalization:
    def unit(n: int) -> Standardizer:
        return Standardizer(np.zeros(n, dtype=np.float32), np.ones(n, dtype=np.float32))

    return Normalization(
        unit(len(WEATHER_CHANNELS)), unit(len(CLIM_CHANNELS)), unit(len(STATIC_FEATURES)),
        unit(len(CROP_FEATURES)),
    )  # fmt: skip


def test_a_snapshot_survives_its_json() -> None:
    snapshot = _snapshot()
    again = SiteSnapshot.from_json(snapshot.to_json())
    assert again.last_day == snapshot.last_day == FIRST + timedelta(days=DAYS - 1)
    assert again.oni == snapshot.oni
    np.testing.assert_allclose(again.weather, snapshot.weather, atol=1e-4)
    assert (again.valid == snapshot.valid).all()


def test_the_inputs_have_the_shapes_the_network_was_exported_with() -> None:
    days = [date(2026, 11, 2) + timedelta(weeks=i) for i in range(3)]
    inputs = plan_inputs(_snapshot(), days, CROPS, _identity_norm(), 0.6, 30)
    n, c = len(days), len(CROPS)
    assert inputs.weather.shape == (n, len(WEATHER_CHANNELS), HISTORY_DAYS)
    assert inputs.clim.shape == (n, len(CLIM_CHANNELS), AHEAD_DAYS)
    assert inputs.static.shape == (n, len(STATIC_FEATURES))
    assert inputs.crops.shape == (c, len(CROP_FEATURES))
    assert inputs.prior.shape == (n, c, 5)
    assert inputs.climatology.b0.shape == (n, c, len(LABELS))


def test_a_sowing_after_the_snapshot_reads_its_latest_year() -> None:
    snapshot = _snapshot()
    plan = climatology_plan(snapshot, [snapshot.last_day + timedelta(days=40)], CROPS, 0.6, 30)
    assert plan.contexts[0].history_end == snapshot.last_day


def test_a_sowing_inside_the_snapshot_reads_the_day_before() -> None:
    snapshot = _snapshot()
    sowing = snapshot.last_day - timedelta(days=10)
    plan = climatology_plan(snapshot, [sowing], CROPS, 0.6, 30)
    assert plan.contexts[0].history_end == sowing - timedelta(days=1)


def test_without_a_complete_year_before_sowing_nothing_is_invented() -> None:
    snapshot = _snapshot(valid_days=200)
    with pytest.raises(IncompleteHistoryError):
        climatology_plan(snapshot, [snapshot.last_day + timedelta(days=1)], CROPS, 0.6, 30)


def test_the_latest_oni_stands_in_when_the_due_season_is_not_published() -> None:
    snapshot = _snapshot()
    near = climatology_plan(snapshot, [date(2026, 11, 2)], CROPS, 0.6, 30)
    far = climatology_plan(snapshot, [date(2027, 1, 4)], CROPS, 0.6, 30)
    assert not near.contexts[0].oni_latest_published
    assert far.contexts[0].oni_latest_published


def test_b0_is_a_point_estimate_within_the_oracle_ranges() -> None:
    outputs = decode_b0(climatology_plan(_snapshot(), [date(2026, 11, 2)], CROPS, 0.6, 30))
    q = outputs.predictions.rel_yield
    assert (q[..., 0] == q[..., 2]).all()
    assert ((q >= 0) & (q <= 1)).all()
    assert set(np.unique(outputs.predictions.success)) <= {0.0, 1.0}
    cycle = np.array([c.cycle_days for c in CROPS])
    assert (outputs.heat_days <= cycle).all()


def test_the_served_climatology_is_trainings_for_a_year_outside_the_baseline() -> None:
    rng = np.random.default_rng(5)
    day0, baseline = date(1991, 1, 1), YearSpan(1991, 1995)
    n = (date(1997, 1, 1) - day0).days
    t, rain, tmax, tmin, et0 = (rng.normal(20, 3, n) for _ in range(5))

    served = served_climatology(t, rain, tmax, tmin, et0, day0, baseline, 31)
    trained = leave_one_out(t, rain, tmax, tmin, et0, day0, baseline, range(1996, 1997), 31)

    np.testing.assert_allclose(served, trained[0])
