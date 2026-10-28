from datetime import timedelta
from itertools import product

import pytest

from app.autonomy.gate import AutonomyGate, GateContext
from app.autonomy.policy import AutonomyPolicy, load_autonomy_policy
from app.domain.enums import ActionType, AutonomyLevel, GateOutcome, strictest
from app.domain.violations import RuleCode
from app.phenology.catalog import CropSpec
from tests.builders import BRIEF_ALWAYS_APPROVAL, LIMITS, NOW, SAFE, context, proposal
from tests.conftest import CONFIG_DIR

A, N, P = AutonomyLevel.AUTONOMOUS, AutonomyLevel.NOTIFY, AutonomyLevel.APPROVAL
POLICY = load_autonomy_policy(CONFIG_DIR / "autonomy.yaml")
GATE = AutonomyGate(POLICY, LIMITS)


# --- the three levels ----------------------------------------------------


def test_autonomous_irrigation_within_limits_executes() -> None:
    verdict = GATE.evaluate(proposal(), GateContext(SAFE, None))

    assert verdict.outcome is GateOutcome.EXECUTE
    assert verdict.effective_level is A
    assert verdict.violations == ()
    assert verdict.reason_code is None


def test_notify_action_within_limits_executes_and_notifies() -> None:
    verdict = GATE.evaluate(
        proposal(ActionType.EXTRA_IRRIGATION, {"volume_mm": 5.0}), GateContext(SAFE, None)
    )

    assert verdict.outcome is GateOutcome.EXECUTE_AND_NOTIFY
    assert verdict.effective_level is N


def test_always_approval_type_awaits_approval() -> None:
    verdict = GATE.evaluate(
        proposal(ActionType.FERTILIZER, {"product": "urea", "n_kg_ha": 60.0}),
        GateContext(SAFE, None),
    )

    assert verdict.outcome is GateOutcome.AWAIT_APPROVAL
    assert verdict.reason_code is RuleCode.ALWAYS_APPROVAL_TYPE


@pytest.mark.parametrize("action_type", BRIEF_ALWAYS_APPROVAL)
def test_every_always_approval_type_awaits_approval_even_if_a_stage_says_autonomous(
    action_type: ActionType,
) -> None:
    verdict = GATE.evaluate(proposal(action_type, {"shift_days": 1.0}), GateContext(SAFE, A))

    assert verdict.outcome is GateOutcome.AWAIT_APPROVAL
    assert verdict.effective_level is P


def test_chemical_injection_never_reaches_an_executing_outcome() -> None:
    for stage_level in (None, A, N, P):
        verdict = GATE.evaluate(
            proposal(ActionType.CHEMICAL_INJECTION, {}), GateContext(SAFE, stage_level)
        )
        assert verdict.outcome is GateOutcome.AWAIT_APPROVAL


# --- stage override: stricter of the two, every combination (D006) -------


def policy_with_irrigation_default(level: AutonomyLevel) -> AutonomyPolicy:
    defaults = {**POLICY.defaults, ActionType.IRRIGATION: level}
    return AutonomyPolicy(defaults, POLICY.always_approval, POLICY.revert_window_seconds)


@pytest.mark.parametrize(("default", "stage"), list(product([A, N, P], [None, A, N, P])))
def test_requested_level_is_the_stricter_of_default_and_stage(
    default: AutonomyLevel, stage: AutonomyLevel | None
) -> None:
    gate = AutonomyGate(policy_with_irrigation_default(default), LIMITS)

    verdict = gate.evaluate(proposal(), GateContext(SAFE, stage))

    expected = default if stage is None else strictest(default, stage)
    assert verdict.requested_level is expected
    assert verdict.effective_level is expected  # no violations in SAFE


def test_a_stage_can_never_relax_the_default() -> None:
    gate = AutonomyGate(policy_with_irrigation_default(N), LIMITS)

    verdict = gate.evaluate(proposal(), GateContext(SAFE, A))

    assert verdict.effective_level is N


def test_maturity_stage_tightens_irrigation_to_notify(maize: CropSpec) -> None:
    stage_level = maize.stage("maturity_harvest").level_for(ActionType.IRRIGATION)

    verdict = GATE.evaluate(proposal(), GateContext(SAFE, stage_level))

    assert verdict.outcome is GateOutcome.EXECUTE_AND_NOTIFY


# --- downgrade path: each rule turns the action into APPROVAL ------------

DOWNGRADES = {
    RuleCode.DAILY_IRRIGATION_CAP_EXCEEDED: context(irrigated_mm_on_day=10.0),
    RuleCode.RAIN_FORECAST_ABOVE_LIMIT: context(rain_forecast_mm_24h=8.0),
    RuleCode.IRRIGATION_INTERVAL_TOO_SHORT: context(last_irrigation_at=NOW - timedelta(hours=3)),
    RuleCode.MOISTURE_ABOVE_LIMIT: context(soil_moisture_vwc=36.0),
    RuleCode.MISSING_INPUT: context(rain_forecast_mm_24h=None),
}


@pytest.mark.parametrize("code", list(DOWNGRADES))
@pytest.mark.parametrize(
    ("action_type", "level"),
    [(ActionType.IRRIGATION, A), (ActionType.EXTRA_IRRIGATION, N)],
)
def test_each_irrigation_rule_downgrades_to_approval(
    code: RuleCode, action_type: ActionType, level: AutonomyLevel
) -> None:
    verdict = GATE.evaluate(proposal(action_type), GateContext(DOWNGRADES[code], None))

    assert verdict.requested_level is level
    assert verdict.effective_level is P
    assert verdict.outcome is GateOutcome.AWAIT_APPROVAL
    assert verdict.reason_code is code


def test_rain_blocked_irrigation_is_pending_approval_with_the_rain_rule() -> None:
    verdict = GATE.evaluate(proposal(), GateContext(context(rain_forecast_mm_24h=8.0), None))

    assert verdict.outcome is GateOutcome.AWAIT_APPROVAL
    assert verdict.violations[0].params == {"forecast_mm": 8.0, "limit_mm": 5.0}


@pytest.mark.parametrize(("shift", "expected"), [(2.0, N), (-2.0, N), (3.0, P), (-3.0, P)])
def test_calendar_shift_over_two_days_downgrades(shift: float, expected: AutonomyLevel) -> None:
    verdict = GATE.evaluate(
        proposal(ActionType.CALENDAR_SHIFT, {"shift_days": shift}), GateContext(SAFE, None)
    )

    assert verdict.effective_level is expected
    if expected is P:
        assert verdict.reason_code is RuleCode.CALENDAR_SHIFT_TOO_LARGE


def test_every_violation_is_listed_not_only_the_first() -> None:
    hostile = context(irrigated_mm_on_day=10.0, rain_forecast_mm_24h=8.0)

    verdict = GATE.evaluate(proposal(), GateContext(hostile, None))

    assert [v.code for v in verdict.violations] == [
        RuleCode.DAILY_IRRIGATION_CAP_EXCEEDED,
        RuleCode.RAIN_FORECAST_ABOVE_LIMIT,
    ]


# --- emergency stop (D022) -----------------------------------------------

STOPPED = context(emergency_stop_active=True)


def test_emergency_stop_sends_irrigation_to_approval_citing_the_stop() -> None:
    verdict = GATE.evaluate(proposal(), GateContext(STOPPED, None))

    assert verdict.outcome is GateOutcome.AWAIT_APPROVAL
    assert verdict.reason_code is RuleCode.EMERGENCY_STOP_ACTIVE


def test_emergency_stop_leads_even_for_always_approval_types() -> None:
    verdict = GATE.evaluate(
        proposal(ActionType.FERTILIZER, {"n_kg_ha": 60.0}), GateContext(STOPPED, None)
    )

    assert [v.code for v in verdict.violations] == [
        RuleCode.EMERGENCY_STOP_ACTIVE,
        RuleCode.ALWAYS_APPROVAL_TYPE,
    ]


@pytest.mark.parametrize(
    ("action_type", "outcome"),
    [
        (ActionType.STOP_IRRIGATION, GateOutcome.EXECUTE),  # the only exemption
        (ActionType.STRESS_ALERT, GateOutcome.EXECUTE),  # out of scope
        (ActionType.STAGE_REPORT, GateOutcome.EXECUTE),  # out of scope
    ],
)
def test_emergency_stop_still_lets_valves_close_and_alerts_through(
    action_type: ActionType, outcome: GateOutcome
) -> None:
    verdict = GATE.evaluate(proposal(action_type, {}), GateContext(STOPPED, None))

    assert verdict.outcome is outcome
    assert verdict.violations == ()
