import numpy as np

from fieldpilot_planner.oracle.factors import trapezoid, water_factor
from fieldpilot_planner.oracle.water_balance import run_season, water_stress_coefficient


def test_ks_follows_fao56_example_39_rows() -> None:
    # FAO-56 Example 39 (beans, TAW 110 mm, RAW 44 mm): Ks without salinity.
    depletion = np.array([40.0, 44.0, 50.0, 60.0, 80.0, 110.0])
    ks = water_stress_coefficient(depletion, taw=110.0, raw=44.0)
    np.testing.assert_allclose(ks, [1.0, 1.0, 0.91, 0.76, 0.45, 0.0], atol=0.01)


def test_wet_season_has_no_stress_and_no_irrigation() -> None:
    rain = np.full((2, 30), 10.0)
    etc = np.full((2, 30), 5.0)
    season = run_season(rain, etc, taw=100.0, depletion_fraction=0.5,
                        initial_depletion=np.zeros(2), irrigate=True)  # fmt: skip
    np.testing.assert_allclose(season.eta_mm, season.etc_mm)
    np.testing.assert_allclose(season.irrigation_mm, 0.0)


def test_dry_season_stresses_rainfed_and_irrigation_refills() -> None:
    rain = np.zeros((1, 60))
    etc = np.full((1, 60), 5.0)
    rainfed = run_season(rain, etc, 100.0, 0.5, np.zeros(1), irrigate=False)
    irrigated = run_season(rain, etc, 100.0, 0.5, np.zeros(1), irrigate=True)
    assert rainfed.eta_mm[0] < rainfed.etc_mm[0]
    assert irrigated.eta_mm[0] == irrigated.etc_mm[0]
    assert irrigated.irrigation_mm[0] > 0
    assert 0 <= rainfed.final_depletion_mm[0] <= 100.0


def test_trapezoid_and_water_factor() -> None:
    x = np.array([5.0, 10.0, 15.0, 20.0, 30.0, 40.0, 47.0])
    np.testing.assert_allclose(trapezoid(x, 10, 18, 33, 47), [0, 0, 0.625, 1, 1, 0.5, 0])
    # FAO-33: 20 % ET deficit with Ky 1.25 -> 25 % yield loss.
    np.testing.assert_allclose(water_factor(np.array([80.0]), np.array([100.0]), 1.25), [0.75])
