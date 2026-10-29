"""RevertService: the backend decides in simulated time (D007, D009, D011)."""

from collections.abc import Callable
from datetime import timedelta

import pytest

from app.domain.enums import ActionType, EventKind, TaskStatus
from app.persistence.unit_of_work import SqlUnitOfWork
from app.services.revert import RevertRefusal, RevertRefusedError
from app.simulator.clock import SimClock
from tests.fakes import FakeWall
from tests.integration.services.world import DAY1, WINDOW, World

SECOND = timedelta(seconds=1)
TOMORROW = DAY1 + timedelta(days=1)


@pytest.fixture
def world(uow: Callable[[], SqlUnitOfWork]) -> World:
    return World(uow)


def scheduled_notify(world: World) -> int:
    task = world.proposals.propose(world.action(ActionType.EXTRA_IRRIGATION, 10.0, TOMORROW)).task
    assert task.status is TaskStatus.SCHEDULED and task.id is not None
    return task.id


def running_notify(world: World, volume_mm: float = 10.0) -> int:
    task = world.proposals.propose(world.action(ActionType.EXTRA_IRRIGATION, volume_mm)).task
    assert task.status is TaskStatus.EXECUTED and task.id is not None
    return task.id


def test_revert_of_a_scheduled_task_cancels_it_and_nothing_executes(world: World) -> None:
    task_id = scheduled_notify(world)

    result = world.revert.revert(task_id, "farmer")

    assert result.task.status is TaskStatus.REVERTED
    assert (result.requested_mm, result.applied_mm, result.applied_liters) == (10.0, 0.0, 0.0)
    assert world.events(EventKind.EXECUTION_REQUESTED, task_id) == []
    assert world.events(EventKind.EXECUTION, task_id) == []


def test_revert_mid_irrigation_stops_it_and_records_the_water(world: World) -> None:
    task_id = running_notify(world)
    world.clock.advance(timedelta(hours=1, minutes=30))

    result = world.revert.revert(task_id, "farmer")

    assert result.applied_mm == 9.0  # exact: 6 mm/h x 1.5 h, below the 10 mm target
    assert result.applied_liters == 45_000.0  # 9 mm x 5000 m2
    assert not world.valve_open()
    [event] = world.events(EventKind.REVERT, task_id)
    assert event.inputs == {
        "status_before": "executed",
        "revert_deadline": (DAY1 + WINDOW).isoformat(),
        "requested_mm": 10.0,
        "applied_mm": 9.0,
        "applied_liters": 45_000.0,
    }


def test_revert_of_an_applied_irrigation_is_refused_and_changes_nothing(world: World) -> None:
    task_id = running_notify(world)
    world.clock.advance(timedelta(hours=2))  # 10 mm at 6 mm/h ends after 1 h 40 min

    with pytest.raises(RevertRefusedError) as refused:
        world.revert.revert(task_id, "farmer")

    assert refused.value.reason is RevertRefusal.ALREADY_APPLIED
    assert world.task(task_id).status is TaskStatus.EXECUTED
    assert world.events(EventKind.REVERT, task_id) == []
    [event] = world.events(EventKind.REVERT_REFUSED, task_id)
    assert event.rule == "already_applied"
    assert (event.inputs["applied_mm"], event.inputs["applied_liters"]) == (10.0, 50_000.0)


def test_revert_one_second_before_the_deadline_is_accepted(world: World) -> None:
    task_id = scheduled_notify(world)
    world.clock.advance(WINDOW - SECOND)

    assert world.revert.revert(task_id, "farmer").task.status is TaskStatus.REVERTED


def test_revert_at_the_deadline_is_refused(world: World) -> None:
    task_id = scheduled_notify(world)
    world.clock.advance(WINDOW)

    with pytest.raises(RevertRefusedError) as refused:
        world.revert.revert(task_id, "farmer")

    assert refused.value.reason is RevertRefusal.WINDOW_CLOSED
    assert world.task(task_id).status is TaskStatus.SCHEDULED
    [event] = world.events(EventKind.REVERT_REFUSED, task_id)
    assert event.inputs["applied_mm"] == 0.0


def test_a_task_without_a_window_is_not_revertible(world: World) -> None:
    task = world.proposals.propose(world.action()).task  # autonomous

    with pytest.raises(RevertRefusedError) as refused:
        world.revert.revert(task.id or 0, "farmer")

    assert refused.value.reason is RevertRefusal.NOT_REVERTIBLE
    assert world.revert.window(task) is None


def test_a_reverted_task_cannot_be_reverted_again(world: World) -> None:
    task_id = scheduled_notify(world)
    world.revert.revert(task_id, "farmer")

    with pytest.raises(RevertRefusedError) as refused:
        world.revert.revert(task_id, "farmer")

    assert refused.value.reason is RevertRefusal.NOT_REVERTIBLE


def test_a_reverted_irrigation_counts_the_water_it_applied(world: World) -> None:
    task_id = running_notify(world)
    world.clock.advance(timedelta(hours=1, minutes=30))
    world.revert.revert(task_id, "farmer")

    context = world.context.context_for(world.action(at=DAY1 + timedelta(hours=13)))

    assert context.safety.irrigated_mm_on_day == 9.0  # not 0 and not the 10 requested


# --- D011: a paused clock pauses the window -------------------------------


def test_paused_clock_keeps_the_window_open_and_the_countdown_frozen(
    uow: Callable[[], SqlUnitOfWork],
) -> None:
    wall = FakeWall(DAY1)
    clock = SimClock.start(DAY1, wall, speed_factor=360.0, paused=True)
    world = World(uow, clock)
    task_id = scheduled_notify(world)
    before = world.revert.window(world.task(task_id))

    wall.tick(timedelta(days=30))  # a month of real time while paused
    frozen = world.revert.window(world.task(task_id))

    assert before is not None and frozen is not None
    assert frozen.remaining == before.remaining == WINDOW
    assert frozen.open is True
    assert world.revert.revert(task_id, "farmer").task.status is TaskStatus.REVERTED


def test_resuming_past_the_deadline_closes_the_window(uow: Callable[[], SqlUnitOfWork]) -> None:
    wall = FakeWall(DAY1)
    clock = SimClock.start(DAY1, wall, speed_factor=360.0, paused=True)
    world = World(uow, clock)
    task_id = scheduled_notify(world)

    clock.resume()
    wall.tick(WINDOW / 360)  # exactly the window in simulated time

    window = world.revert.window(world.task(task_id))
    assert window is not None and window.open is False and window.remaining == timedelta(0)
    with pytest.raises(RevertRefusedError):
        world.revert.revert(task_id, "farmer")
