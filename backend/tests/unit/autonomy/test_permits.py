"""Only AutonomyGate can issue an ExecutionPermit (D037)."""

import dataclasses

import pytest

from app.autonomy.gate import (
    AutonomyGate,
    ExecutionPermit,
    FarmerApproval,
    GateContext,
    unapproved,
)
from app.autonomy.policy import load_autonomy_policy
from app.domain.enums import ActionType, AutonomyLevel, GateOutcome
from app.domain.violations import RuleCode
from tests.builders import LIMITS, SAFE, context, proposal
from tests.conftest import CONFIG_DIR

GATE = AutonomyGate(load_autonomy_policy(CONFIG_DIR / "autonomy.yaml"), LIMITS)


def test_a_permit_cannot_be_built_by_hand() -> None:
    with pytest.raises(PermissionError, match="only be issued by AutonomyGate"):
        ExecutionPermit(
            proposal_key="proposal-x",
            action_type=ActionType.IRRIGATION,
            zone_id=2,
            params={"volume_mm": 15.0},
            level=AutonomyLevel.AUTONOMOUS,
        )


def test_a_permit_cannot_be_copied_with_changes() -> None:
    permit = GATE.authorize(proposal(), GateContext(SAFE, None)).permit
    assert permit is not None

    with pytest.raises(PermissionError):
        dataclasses.replace(permit, zone_id=3)


def test_autonomous_verdict_comes_with_a_permit_for_that_action() -> None:
    action = proposal()
    auth = GATE.authorize(action, GateContext(SAFE, None))

    assert auth.verdict.outcome is GateOutcome.EXECUTE
    assert auth.permit is not None
    assert auth.permit.proposal_key == action.proposal_key
    assert auth.permit.action_type is ActionType.IRRIGATION
    assert auth.permit.zone_id == 2
    assert auth.permit.params == {"volume_mm": 15.0}
    assert auth.permit.level is AutonomyLevel.AUTONOMOUS


def test_notify_verdict_comes_with_a_notify_permit() -> None:
    auth = GATE.authorize(
        proposal(ActionType.EXTRA_IRRIGATION, {"volume_mm": 5.0}), GateContext(SAFE, None)
    )

    assert auth.verdict.outcome is GateOutcome.EXECUTE_AND_NOTIFY
    assert auth.permit is not None and auth.permit.level is AutonomyLevel.NOTIFY


def test_approval_verdict_never_comes_with_a_permit() -> None:
    auth = GATE.authorize(proposal(), GateContext(context(rain_forecast_mm_24h=8.0), None))

    assert auth.verdict.outcome is GateOutcome.AWAIT_APPROVAL
    assert auth.permit is None


def test_always_approval_type_never_comes_with_a_permit() -> None:
    auth = GATE.authorize(proposal(ActionType.CHEMICAL_INJECTION, {}), GateContext(SAFE, None))

    assert auth.permit is None


def test_authorize_returns_the_same_verdict_as_evaluate() -> None:
    action, ctx = proposal(), GateContext(context(irrigated_mm_on_day=10.0), None)

    assert GATE.authorize(action, ctx).verdict == GATE.evaluate(action, ctx)


# Farmer approvals (D062).

RAIN = frozenset({RuleCode.RAIN_FORECAST_ABOVE_LIMIT})


def _approved(*codes: RuleCode) -> FarmerApproval:
    return FarmerApproval("farmer", frozenset(codes))


def test_an_approval_covers_the_rule_the_farmer_saw() -> None:
    auth = GATE.authorize_approved(
        proposal(), GateContext(context(rain_forecast_mm_24h=8.0), None), _approved(*RAIN)
    )

    assert auth.verdict.outcome is GateOutcome.AWAIT_APPROVAL
    assert auth.permit is not None
    assert auth.permit.level is AutonomyLevel.APPROVAL
    assert auth.permit.approved_by == "farmer"


def test_the_same_rule_with_a_new_number_is_still_covered() -> None:
    auth = GATE.authorize_approved(
        proposal(), GateContext(context(rain_forecast_mm_24h=12.0), None), _approved(*RAIN)
    )

    assert auth.permit is not None


def test_an_approval_never_covers_the_emergency_stop() -> None:
    stopped = context(rain_forecast_mm_24h=8.0, emergency_stop_active=True)
    approval = _approved(RuleCode.RAIN_FORECAST_ABOVE_LIMIT, RuleCode.EMERGENCY_STOP_ACTIVE)

    auth = GATE.authorize_approved(proposal(), GateContext(stopped, None), approval)

    assert auth.permit is None
    assert unapproved(auth.verdict, approval)[0].code is RuleCode.EMERGENCY_STOP_ACTIVE


def test_a_new_violation_is_not_covered() -> None:
    wet = context(rain_forecast_mm_24h=8.0, soil_moisture_vwc=30.0, field_capacity_vwc=32.0)

    auth = GATE.authorize_approved(proposal(), GateContext(wet, None), _approved(*RAIN))

    assert auth.permit is None
    assert [v.code for v in unapproved(auth.verdict, _approved(*RAIN))] == [
        RuleCode.MOISTURE_ABOVE_LIMIT
    ]


def test_an_action_the_gate_now_allows_gets_its_normal_permit() -> None:
    auth = GATE.authorize_approved(proposal(), GateContext(SAFE, None), _approved(*RAIN))

    assert auth.permit is not None
    assert auth.permit.level is AutonomyLevel.AUTONOMOUS
    assert auth.permit.approved_by is None


def test_plain_authorize_never_carries_an_approval() -> None:
    permit = GATE.authorize(proposal(), GateContext(SAFE, None)).permit

    assert permit is not None and permit.approved_by is None
