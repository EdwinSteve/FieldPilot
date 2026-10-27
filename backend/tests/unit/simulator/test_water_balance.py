import pytest

from app.simulator.water_balance import SoilParams, WaterInputs, crop_et_mm, step_water_balance

SOIL = SoilParams(
    root_depth_mm=300.0,
    field_capacity_vwc=32.0,
    wilting_point_vwc=12.0,
    saturation_vwc=45.0,
    drainage_per_day=0.5,
)
FIXED_KC = 1.2  # fixed here so results do not depend on the phenology engine


def inputs(
    *, rain: float = 0.0, irrigation: float = 0.0, et0: float = 0.0, days: float = 1.0
) -> WaterInputs:
    return WaterInputs(
        rain_mm=rain,
        irrigation_mm=irrigation,
        et0_mm=et0,
        crop_coefficient=FIXED_KC,
        interval_days=days,
    )


def test_rain_raises_moisture() -> None:
    step = step_water_balance(20.0, inputs(rain=6.0), SOIL)

    assert step.vwc == pytest.approx(22.0)  # 6 mm over 300 mm = +2 points


def test_small_rain_exactly_at_field_capacity_does_not_drain() -> None:
    step = step_water_balance(SOIL.field_capacity_vwc, inputs(rain=3.0, days=15 / 1440), SOIL)

    assert step.drained_mm == 0.0
    assert step.vwc == pytest.approx(33.0)


def test_excess_above_field_capacity_drains_at_the_configured_rate() -> None:
    step = step_water_balance(35.0, inputs(days=1.0), SOIL)  # 9 mm above capacity

    assert step.drained_mm == pytest.approx(4.5)
    assert step.vwc == pytest.approx(33.5)


def test_crop_et_uses_the_given_crop_coefficient() -> None:
    assert crop_et_mm(4.0, FIXED_KC) == pytest.approx(4.8)


def test_et_lowers_moisture_by_et0_times_kc() -> None:
    step = step_water_balance(25.0, inputs(et0=4.0), SOIL)

    assert step.et_mm == pytest.approx(4.8)
    assert step.vwc == pytest.approx(25.0 - 1.6)


def test_moisture_never_drops_below_wilting_point() -> None:
    step = step_water_balance(12.5, inputs(et0=10.0), SOIL)

    assert step.vwc == pytest.approx(SOIL.wilting_point_vwc)
    assert step.et_mm == pytest.approx(1.5)  # only the water above the floor


def test_water_above_saturation_runs_off() -> None:
    step = step_water_balance(44.0, inputs(rain=30.0, days=15 / 1440), SOIL)

    assert step.vwc == pytest.approx(SOIL.saturation_vwc)
    assert step.runoff_mm > 0


def test_water_is_conserved() -> None:
    start = 30.0
    step = step_water_balance(start, inputs(rain=5.0, irrigation=7.0, et0=3.0), SOIL)

    stored_delta = SOIL.water_mm(step.vwc) - SOIL.water_mm(start)
    assert stored_delta == pytest.approx(5.0 + 7.0 - step.et_mm - step.drained_mm - step.runoff_mm)


@pytest.mark.parametrize(
    "bad",
    [
        {"wilting_point_vwc": 33.0},
        {"saturation_vwc": 30.0},
        {"root_depth_mm": 0.0},
        {"drainage_per_day": 1.5},
    ],
)
def test_inconsistent_soil_is_rejected(bad: dict[str, float]) -> None:
    with pytest.raises(ValueError, match="inconsistent"):
        SoilParams(**bad)
