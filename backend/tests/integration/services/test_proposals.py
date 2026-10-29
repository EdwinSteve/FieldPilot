"""ProposalService: one task per proposal (D023), decided from stored facts (D035)."""

from collections.abc import Callable
from datetime import timedelta

import pytest

from app.domain.enums import ActionType, EventKind, GateOutcome, TaskStatus
from app.domain.violations import RuleCode
from app.persistence.unit_of_work import SqlUnitOfWork
from tests.integration.services.world import DAY1, WINDOW, World


@pytest.fixture
def world(uow: Callable[[], SqlUnitOfWork]) -> World:
    return World(uow)


def test_autonomous_irrigation_runs_now_with_events_in_order(world: World) -> None:
    result = world.proposals.propose(world.action())

    assert result.verdict.outcome is GateOutcome.EXECUTE
    assert result.task.status is TaskStatus.EXECUTED
    assert world.valve_open()
    kinds = [e.kind for e in world.events(task_id=result.task.id)]
    assert kinds == [
        EventKind.PROPOSAL,
        EventKind.GATE_VERDICT,
        EventKind.EXECUTION_REQUESTED,
        EventKind.EXECUTION,
    ]


def test_the_same_proposal_twice_returns_the_same_task_and_verdict(world: World) -> None:
    first = world.proposals.propose(world.action())
    again = world.proposals.propose(world.action(rationale="Reworded by the LLM."))

    assert again.task.id == first.task.id
    assert again.verdict == first.verdict
    assert again.already_decided_at == DAY1
    assert first.already_decided_at is None
    assert len(world.events(EventKind.PROPOSAL)) == 1
    assert len(world.events(EventKind.GATE_VERDICT)) == 1
    assert len(world.events(EventKind.EXECUTION_REQUESTED)) == 1


def test_notify_action_gets_a_backend_deadline_and_a_notification(world: World) -> None:
    result = world.proposals.propose(world.action(ActionType.EXTRA_IRRIGATION, 10.0))

    assert result.verdict.outcome is GateOutcome.EXECUTE_AND_NOTIFY
    assert result.task.revert_deadline == DAY1 + WINDOW
    with world.uow() as u:
        [notification] = u.notifications.list()
    assert notification.revert_deadline == DAY1 + WINDOW
    assert notification.task_id == result.task.id


def test_approval_waits_and_never_reaches_the_actuator(world: World) -> None:
    world.forecast.mm = 8.0

    result = world.proposals.propose(world.action())

    assert result.task.status is TaskStatus.PENDING_APPROVAL
    assert result.verdict.reason_code is RuleCode.RAIN_FORECAST_ABOVE_LIMIT
    assert world.events(EventKind.EXECUTION_REQUESTED) == []
    assert not world.valve_open()


def test_missing_forecast_waits_for_approval(world: World) -> None:
    world.forecast.mm = None

    result = world.proposals.propose(world.action())

    assert result.verdict.reason_code is RuleCode.MISSING_INPUT
    assert result.task.status is TaskStatus.PENDING_APPROVAL


def test_a_decision_row_is_stored_with_the_verdict(world: World) -> None:
    result = world.proposals.propose(world.action())

    with world.uow() as u:
        [decision] = u.decisions.list_by_task(result.task.id or 0)
    assert decision.outcome is GateOutcome.EXECUTE
    assert decision.effective_level is result.task.effective_level


def test_scheduled_irrigations_count_toward_the_daily_cap(world: World) -> None:
    tomorrow = DAY1 + timedelta(days=1)  # 06:00 local
    world.proposals.propose(world.action(at=tomorrow))

    second = world.proposals.propose(
        world.action(volume_mm=10.0, at=tomorrow + timedelta(hours=13))
    )

    assert second.verdict.reason_code is RuleCode.DAILY_IRRIGATION_CAP_EXCEEDED
    assert second.task.status is TaskStatus.PENDING_APPROVAL


def test_a_future_irrigation_stays_scheduled_and_closed(world: World) -> None:
    result = world.proposals.propose(world.action(at=DAY1 + timedelta(days=1)))

    assert result.task.status is TaskStatus.SCHEDULED
    assert not world.valve_open()
    assert world.events(EventKind.EXECUTION_REQUESTED) == []
