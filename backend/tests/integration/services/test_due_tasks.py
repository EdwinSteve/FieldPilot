"""DueTaskRunner: scheduled tasks wait for their time and are re-evaluated (D009, D033)."""

from collections.abc import Callable
from datetime import timedelta

import pytest

from app.domain.enums import ActionType, EventKind, GateOutcome, TaskStatus
from app.domain.violations import RuleCode
from app.persistence.unit_of_work import SqlUnitOfWork
from tests.integration.services.world import DAY1, World

TOMORROW = DAY1 + timedelta(days=1)  # 06:00 local, 24 h after the first irrigation


@pytest.fixture
def world(uow: Callable[[], SqlUnitOfWork]) -> World:
    return World(uow)


def test_d009_next_day_extra_irrigation_is_reverted_while_scheduled(world: World) -> None:
    first = world.proposals.propose(world.action(volume_mm=15.0))
    assert first.task.status is TaskStatus.EXECUTED
    extra = world.proposals.propose(world.action(ActionType.EXTRA_IRRIGATION, 10.0, TOMORROW))
    assert extra.verdict.outcome is GateOutcome.EXECUTE_AND_NOTIFY
    extra_id = extra.task.id

    world.clock.advance(timedelta(hours=2))
    assert world.due.run_due(world.clock.now()) == []
    assert world.task(extra_id).status is TaskStatus.SCHEDULED

    world.revert.revert(extra_id or 0, "farmer")
    world.clock.advance(timedelta(hours=23))  # past scheduled_for
    assert world.due.run_due(world.clock.now()) == []

    assert world.task(extra_id).status is TaskStatus.REVERTED
    assert world.events(EventKind.EXECUTION_REQUESTED, extra_id) == []
    assert world.events(EventKind.EXECUTION, extra_id) == []
    day1 = world.context.context_for(world.action(at=DAY1 + timedelta(hours=1)))
    assert day1.safety.irrigated_mm_on_day == 15.0


def test_a_scheduled_task_stays_scheduled_until_its_time(world: World) -> None:
    extra = world.proposals.propose(world.action(ActionType.EXTRA_IRRIGATION, 10.0, TOMORROW))

    world.clock.advance(timedelta(hours=23, minutes=59))
    assert world.due.run_due(world.clock.now()) == []
    assert world.task(extra.task.id).status is TaskStatus.SCHEDULED

    world.clock.advance(timedelta(minutes=1))
    [executed] = world.due.run_due(world.clock.now())

    assert executed.status is TaskStatus.EXECUTED
    assert world.valve_open()
    [request] = world.events(EventKind.EXECUTION_REQUESTED, extra.task.id)
    recheck = request.inputs["recheck_verdict"]
    assert isinstance(recheck, dict) and recheck["outcome"] == "execute_notify"


def test_a_due_task_does_not_count_its_own_water(world: World) -> None:
    task = world.proposals.propose(world.action(volume_mm=15.0, at=TOMORROW)).task
    world.clock.advance(timedelta(days=1))

    [executed] = world.due.run_due(world.clock.now())

    assert executed.id == task.id
    assert executed.status is TaskStatus.EXECUTED  # 15 mm, not 15 + 15 > 20


def test_a_due_task_downgraded_by_new_rain_fails_and_names_the_rule(world: World) -> None:
    task = world.proposals.propose(world.action(ActionType.EXTRA_IRRIGATION, 10.0, TOMORROW)).task
    world.forecast.mm = 8.0
    world.clock.advance(timedelta(days=1))

    [failed] = world.due.run_due(world.clock.now())

    assert failed.status is TaskStatus.FAILED
    assert not world.valve_open()
    assert world.events(EventKind.EXECUTION_REQUESTED, task.id) == []
    [event] = world.events(EventKind.EXECUTION_FAILED, task.id)
    assert event.rule == RuleCode.RAIN_FORECAST_ABOVE_LIMIT
    with world.uow() as u:
        messages = [n.message for n in u.notifications.list() if n.task_id == task.id]
    assert (
        "La tarea programada no se ejecutó: pendiente de aprobación por lluvia prevista "
        "(8 mm > 5 mm). Requiere una nueva decisión"
    ) in messages


def test_an_emergency_stop_at_its_time_fails_the_task(world: World) -> None:
    task = world.proposals.propose(world.action(volume_mm=15.0, at=TOMORROW)).task
    world.set_emergency_stop(True)
    world.clock.advance(timedelta(days=1))

    [failed] = world.due.run_due(world.clock.now())

    assert failed.status is TaskStatus.FAILED
    [event] = world.events(EventKind.EXECUTION_FAILED, task.id)
    assert event.rule == RuleCode.EMERGENCY_STOP_ACTIVE
    assert not world.valve_open()


def test_calendar_shift_is_left_scheduled(world: World) -> None:
    task = world.proposals.propose(
        world.action(ActionType.CALENDAR_SHIFT, at=TOMORROW, params={"shift_days": 1.0})
    ).task
    world.clock.advance(timedelta(days=2))

    assert world.due.run_due(world.clock.now()) == []
    assert world.task(task.id).status is TaskStatus.SCHEDULED
