from datetime import timedelta

import pytest

from app.domain.enums import ActionType
from app.domain.violations import RuleCode
from app.safety.rules import (
    CALENDAR_ACTIONS,
    IRRIGATION_ACTIONS,
    check_calendar_shift,
    check_daily_irrigation_cap,
    check_emergency_stop,
    check_irrigation_interval,
    check_moisture,
    check_rain_forecast,
    evaluate_rules,
)
from tests.builders import LIMITS, NOW, SAFE, context, proposal


def test_the_safe_context_passes_every_rule() -> None:
    assert evaluate_rules(proposal(), SAFE, LIMITS) == ()


# --- daily cap: 20 mm allowed, 20.01 not ---------------------------------


@pytest.mark.parametrize(
    ("already", "volume", "violates"),
    [
        (0.0, 20.0, False),  # exactly at the cap
        (0.0, 20.01, True),
        (15.0, 5.0, False),  # existing + new exactly at the cap
        (15.0, 5.01, True),
        (15.0, 10.0, True),  # the README example: 25 mm in one day
    ],
)
def test_daily_cap_boundary(already: float, volume: float, violates: bool) -> None:
    violation = check_daily_irrigation_cap(
        proposal(params={"volume_mm": volume}), context(irrigated_mm_on_day=already), LIMITS
    )

    assert (violation is not None) is violates
    if violation:
        assert violation.code is RuleCode.DAILY_IRRIGATION_CAP_EXCEEDED
        assert violation.params["total_mm"] == pytest.approx(already + volume)
        assert violation.params["limit_mm"] == 20.0


@pytest.mark.parametrize(
    "params", [{}, {"volume_mm": 0.0}, {"volume_mm": -3.0}, {"volume_mm": "x"}]
)
def test_daily_cap_without_a_valid_volume_is_missing_input(params: dict[str, object]) -> None:
    violation = check_daily_irrigation_cap(proposal(params=params), SAFE, LIMITS)  # type: ignore[arg-type]

    assert violation is not None and violation.code is RuleCode.MISSING_INPUT
    assert violation.params == {"input": "volume_mm"}


# --- rain: 5 mm allowed, above not ---------------------------------------


@pytest.mark.parametrize(
    ("forecast", "violates"), [(0.0, False), (5.0, False), (5.01, True), (8.0, True)]
)
def test_rain_forecast_boundary(forecast: float, violates: bool) -> None:
    violation = check_rain_forecast(proposal(), context(rain_forecast_mm_24h=forecast), LIMITS)

    assert (violation is not None) is violates
    if violation:
        assert violation.code is RuleCode.RAIN_FORECAST_ABOVE_LIMIT
        assert violation.params == {"forecast_mm": forecast, "limit_mm": 5.0}


def test_missing_forecast_is_a_violation() -> None:
    violation = check_rain_forecast(proposal(), context(rain_forecast_mm_24h=None), LIMITS)

    assert violation is not None and violation.code is RuleCode.MISSING_INPUT


# --- interval: 12 h allowed, less not ------------------------------------


@pytest.mark.parametrize(
    ("since_last", "violates"),
    [
        (timedelta(hours=12), False),
        (timedelta(hours=13), False),
        (timedelta(hours=11, minutes=59), True),
        (timedelta(hours=2), True),
    ],
)
def test_irrigation_interval_boundary(since_last: timedelta, violates: bool) -> None:
    violation = check_irrigation_interval(
        proposal(), context(last_irrigation_at=NOW - since_last), LIMITS
    )

    assert (violation is not None) is violates
    if violation:
        assert violation.code is RuleCode.IRRIGATION_INTERVAL_TOO_SHORT


def test_interval_is_measured_from_the_scheduled_time_not_from_now() -> None:
    # Irrigated at 06:00 today; the extra irrigation is planned for tomorrow 06:00 (D009).
    tomorrow = proposal(
        ActionType.EXTRA_IRRIGATION, {"volume_mm": 10.0}, scheduled_for=NOW + timedelta(days=1)
    )

    assert check_irrigation_interval(tomorrow, context(last_irrigation_at=NOW), LIMITS) is None


def test_no_previous_irrigation_passes_the_interval() -> None:
    assert check_irrigation_interval(proposal(), context(last_irrigation_at=None), LIMITS) is None


# --- moisture: 85 % of field capacity allowed, above not (D015) ----------


@pytest.mark.parametrize(
    ("vwc", "violates"),
    [
        (34.0, False),  # 34 / 40 = exactly 85 % FC
        (34.004, True),  # 85.01 % FC
        (20.0, False),
    ],
)
def test_moisture_boundary_in_percent_of_field_capacity(vwc: float, violates: bool) -> None:
    violation = check_moisture(
        proposal(), context(soil_moisture_vwc=vwc, field_capacity_vwc=40.0), LIMITS
    )

    assert (violation is not None) is violates
    if violation:
        assert violation.code is RuleCode.MOISTURE_ABOVE_LIMIT
        assert violation.params["moisture_pct_fc"] == pytest.approx(vwc / 40 * 100)


def test_moisture_rule_converts_before_comparing() -> None:
    # 30 % VWC is well below 85 as a raw number, but 30 / 32 = 93.75 % of field capacity.
    violation = check_moisture(
        proposal(), context(soil_moisture_vwc=30.0, field_capacity_vwc=32.0), LIMITS
    )

    assert violation is not None and violation.code is RuleCode.MOISTURE_ABOVE_LIMIT
    assert violation.params["moisture_pct_fc"] == pytest.approx(93.75)


@pytest.mark.parametrize(
    ("changes", "missing"),
    [
        ({"soil_moisture_vwc": None}, "soil_moisture_vwc"),
        ({"field_capacity_vwc": None}, "field_capacity_vwc"),
        ({"field_capacity_vwc": 0.0}, "field_capacity_vwc"),
    ],
)
def test_missing_moisture_inputs_are_violations(changes: dict[str, object], missing: str) -> None:
    violation = check_moisture(proposal(), context(**changes), LIMITS)

    assert violation is not None and violation.code is RuleCode.MISSING_INPUT
    assert violation.params == {"input": missing}


# --- calendar: 2 days allowed, 3 not, both directions (D026) -------------


@pytest.mark.parametrize(
    ("shift", "violates"),
    [(2.0, False), (-2.0, False), (3.0, True), (-3.0, True), (2.01, True), (0.0, False)],
)
@pytest.mark.parametrize("action_type", sorted(CALENDAR_ACTIONS))
def test_calendar_shift_boundary(action_type: ActionType, shift: float, violates: bool) -> None:
    violation = check_calendar_shift(proposal(action_type, {"shift_days": shift}), SAFE, LIMITS)

    assert (violation is not None) is violates
    if violation:
        assert violation.code is RuleCode.CALENDAR_SHIFT_TOO_LARGE
        assert violation.params == {"shift_days": abs(shift), "limit_days": 2.0}


def test_calendar_shift_without_days_is_missing_input() -> None:
    violation = check_calendar_shift(proposal(ActionType.CALENDAR_SHIFT, {}), SAFE, LIMITS)

    assert violation is not None and violation.code is RuleCode.MISSING_INPUT


# --- scope: which rules apply to which actions ---------------------------


@pytest.mark.parametrize("action_type", sorted(set(ActionType) - IRRIGATION_ACTIONS))
def test_irrigation_rules_ignore_other_actions(action_type: ActionType) -> None:
    hostile = context(
        irrigated_mm_on_day=100.0,
        rain_forecast_mm_24h=50.0,
        last_irrigation_at=NOW,
        soil_moisture_vwc=None,
    )
    action = proposal(action_type, {"shift_days": 1.0})

    for rule in (
        check_daily_irrigation_cap,
        check_rain_forecast,
        check_irrigation_interval,
        check_moisture,
    ):
        assert rule(action, hostile, LIMITS) is None


@pytest.mark.parametrize("action_type", sorted(IRRIGATION_ACTIONS))
def test_every_irrigation_rule_applies_to_extra_irrigation_too(action_type: ActionType) -> None:
    hostile = context(irrigated_mm_on_day=20.0, rain_forecast_mm_24h=8.0, last_irrigation_at=NOW)

    codes = {v.code for v in evaluate_rules(proposal(action_type), hostile, LIMITS)}

    assert codes == {
        RuleCode.DAILY_IRRIGATION_CAP_EXCEEDED,
        RuleCode.RAIN_FORECAST_ABOVE_LIMIT,
        RuleCode.IRRIGATION_INTERVAL_TOO_SHORT,
    }


# --- emergency stop (D022) -----------------------------------------------

NOT_BLOCKED = {ActionType.STOP_IRRIGATION, ActionType.STRESS_ALERT, ActionType.STAGE_REPORT}


@pytest.mark.parametrize("action_type", sorted(ActionType))
def test_emergency_stop_blocks_everything_that_adds_water_or_changes_the_plan(
    action_type: ActionType,
) -> None:
    violation = check_emergency_stop(
        proposal(action_type), context(emergency_stop_active=True), LIMITS
    )

    if action_type in NOT_BLOCKED:
        assert violation is None
    else:
        assert violation is not None and violation.code is RuleCode.EMERGENCY_STOP_ACTIVE


def test_emergency_stop_inactive_blocks_nothing() -> None:
    assert check_emergency_stop(proposal(ActionType.FERTILIZER), SAFE, LIMITS) is None


def test_emergency_stop_is_listed_first_among_all_violations() -> None:
    everything_wrong = context(
        emergency_stop_active=True, irrigated_mm_on_day=20.0, rain_forecast_mm_24h=9.0
    )

    violations = evaluate_rules(proposal(), everything_wrong, LIMITS)

    assert violations[0].code is RuleCode.EMERGENCY_STOP_ACTIVE
    assert {v.code for v in violations[1:]} == {
        RuleCode.DAILY_IRRIGATION_CAP_EXCEEDED,
        RuleCode.RAIN_FORECAST_ABOVE_LIMIT,
    }
