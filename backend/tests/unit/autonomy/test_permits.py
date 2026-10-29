"""Only AutonomyGate can issue an ExecutionPermit (D037)."""

import dataclasses

import pytest

from app.autonomy.gate import AutonomyGate, ExecutionPermit, GateContext
from app.autonomy.policy import load_autonomy_policy
from app.domain.enums import ActionType, AutonomyLevel, GateOutcome
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
