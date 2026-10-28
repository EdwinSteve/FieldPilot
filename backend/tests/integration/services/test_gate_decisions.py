import json
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from app.autonomy.gate import AutonomyGate, GateContext
from app.autonomy.policy import load_autonomy_policy
from app.domain.enums import AutonomyLevel, EventKind, GateOutcome
from app.domain.violations import RuleCode
from app.persistence.unit_of_work import SqlUnitOfWork
from app.services.gate_decisions import record_verdict
from app.simulator.clock import SimClock
from tests.builders import LIMITS, NOW, SAFE, context, proposal
from tests.conftest import CONFIG_DIR
from tests.fakes import FakeWall

UowFactory = Callable[[], SqlUnitOfWork]
GATE = AutonomyGate(load_autonomy_policy(CONFIG_DIR / "autonomy.yaml"), LIMITS)


def clock_at(minutes: int = 0) -> SimClock:
    at = NOW + timedelta(minutes=minutes)
    return SimClock.start(at, FakeWall(at), paused=True)


def test_verdict_is_logged_with_inputs_level_rule_and_reason(uow: UowFactory) -> None:
    action = proposal()
    gate_context = GateContext(context(rain_forecast_mm_24h=8.0), None)
    verdict = GATE.evaluate(action, gate_context)

    recorded = record_verdict(uow, clock_at(), action, gate_context, verdict)

    assert recorded.already_decided_at is None
    with uow() as u:
        [event] = u.events.list(kind=EventKind.GATE_VERDICT)
    assert event.idempotency_key == action.proposal_key
    assert event.autonomy_level is AutonomyLevel.APPROVAL
    assert event.rule == RuleCode.RAIN_FORECAST_ABOVE_LIMIT
    assert "rain_forecast_above_limit" in event.reason
    assert event.occurred_at == NOW
    stored: dict[str, Any] = json.loads(json.dumps(event.inputs))
    assert stored["proposal"]["params"] == {"volume_mm": 15.0}
    assert stored["context"]["rain_forecast_mm_24h"] == 8.0
    assert stored["verdict"]["requested_level"] == "autonomous"
    assert stored["verdict"]["violations"] == [
        {"code": "rain_forecast_above_limit", "params": {"forecast_mm": 8.0, "limit_mm": 5.0}}
    ]


def test_an_allowed_action_is_logged_too(uow: UowFactory) -> None:
    action = proposal()
    verdict = GATE.evaluate(action, GateContext(SAFE, None))

    record_verdict(uow, clock_at(), action, GateContext(SAFE, None), verdict)

    with uow() as u:
        [event] = u.events.list(kind=EventKind.GATE_VERDICT)
    assert event.autonomy_level is AutonomyLevel.AUTONOMOUS
    assert event.rule is None


def test_a_retried_proposal_returns_the_earlier_verdict(uow: UowFactory) -> None:
    first = proposal()
    rejected_context = GateContext(context(rain_forecast_mm_24h=8.0), None)
    record_verdict(
        uow, clock_at(0), first, rejected_context, GATE.evaluate(first, rejected_context)
    )

    # Same content, re-sent later by the agent; rain no longer forecast.
    retry = proposal()
    clear = GateContext(SAFE, None)
    recorded = record_verdict(uow, clock_at(30), retry, clear, GATE.evaluate(retry, clear))

    assert recorded.already_decided_at == NOW
    assert recorded.verdict.outcome is GateOutcome.AWAIT_APPROVAL
    assert recorded.verdict.reason_code is RuleCode.RAIN_FORECAST_ABOVE_LIMIT
    with uow() as u:
        assert len(u.events.list(kind=EventKind.GATE_VERDICT)) == 1


def test_a_different_volume_is_a_new_proposal(uow: UowFactory) -> None:
    for volume in (15.0, 10.0):
        action = proposal(params={"volume_mm": volume})
        ctx = GateContext(SAFE, None)
        record_verdict(uow, clock_at(), action, ctx, GATE.evaluate(action, ctx))

    with uow() as u:
        assert len(u.events.list(kind=EventKind.GATE_VERDICT)) == 2
