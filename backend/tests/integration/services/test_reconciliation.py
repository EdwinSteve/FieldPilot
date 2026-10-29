"""D032: an irrigation cut by a restart is reported, never hidden or invented."""

from collections.abc import Callable
from datetime import timedelta

import pytest

from app.domain.enums import ActionType, EventKind, TaskStatus
from app.persistence.unit_of_work import SqlUnitOfWork
from app.services.reconciliation import reconcile_executions
from tests.integration.services.world import DAY1, MESSAGES, World


@pytest.fixture
def world(uow: Callable[[], SqlUnitOfWork]) -> World:
    return World(uow)


def restart_and_reconcile(world: World):  # type: ignore[no-untyped-def]
    world.build_services()  # empty simulator and actuator, as after a restart (D014)
    return reconcile_executions(world.uow, world.clock, world.actuator, MESSAGES)


def test_a_running_irrigation_cut_by_a_restart_is_reported_as_unknown(world: World) -> None:
    task = world.proposals.propose(world.action(volume_mm=15.0)).task
    world.clock.advance(timedelta(minutes=30))

    report = restart_and_reconcile(world)

    assert report.interrupted == (task.id,)
    assert report.simulator_state_resumed is False
    assert world.task(task.id).status is TaskStatus.EXECUTED
    [event] = world.events(EventKind.NOTIFICATION, task.id)
    assert event.idempotency_key == f"interrupted:task-{task.id}:attempt-1"
    assert event.inputs["requested_mm"] == 15.0
    assert event.inputs["applied_mm"] is None
    with world.uow() as u:
        [notification] = u.notifications.list()
    assert "pudo haber seguido después del reinicio" in notification.message
    assert "se desconoce" in notification.message
    assert "15 mm" in notification.message


def test_a_second_restart_does_not_repeat_the_report(world: World) -> None:
    world.proposals.propose(world.action(volume_mm=15.0))
    restart_and_reconcile(world)

    second = restart_and_reconcile(world)

    assert second.interrupted == ()
    with world.uow() as u:
        assert len(u.notifications.list()) == 1


def test_an_irrigation_that_ended_while_the_backend_ran_is_not_reported(world: World) -> None:
    world.proposals.propose(world.action(volume_mm=15.0))  # ends after 2.5 h
    world.clock.advance(timedelta(hours=3))
    world.proposals.propose(  # the backend logged something after the run ended
        world.action(ActionType.STRESS_ALERT, params={"note": "ok"})
    )

    assert restart_and_reconcile(world).interrupted == ()


def test_an_interrupted_irrigation_counts_its_requested_water(world: World) -> None:
    world.proposals.propose(world.action(volume_mm=15.0))
    restart_and_reconcile(world)

    context = world.context.context_for(world.action(at=DAY1 + timedelta(hours=13)))

    assert context.safety.irrigated_mm_on_day == 15.0


def test_the_same_process_does_not_report_its_own_running_irrigation(world: World) -> None:
    world.proposals.propose(world.action(volume_mm=15.0))

    report = reconcile_executions(world.uow, world.clock, world.actuator, MESSAGES)

    assert report.interrupted == ()
