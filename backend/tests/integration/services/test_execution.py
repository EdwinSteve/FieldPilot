"""Write-ahead execution and startup reconciliation (D013): never twice, never late."""

from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest

from app.actuation.ports import ExecutionResult
from app.autonomy.gate import ExecutionPermit
from app.domain.enums import EventKind, TaskStatus
from app.domain.models import Task
from app.persistence.unit_of_work import SqlUnitOfWork
from app.services.reconciliation import reconcile_executions
from tests.fakes import FakeEmergencyStop
from tests.integration.services.world import MESSAGES, RATE, World


class SimulatedCrashError(Exception):
    """A process death between the two transactions (not a DomainError)."""


class CrashingActuator:
    """Wraps the real actuator and dies before or after the valve command."""

    def __init__(self, inner: Any, after_command: bool) -> None:
        self.inner = inner
        self.after_command = after_command

    def execute(self, permit: ExecutionPermit, task: Task, key: str) -> ExecutionResult:
        if self.after_command:
            self.inner.execute(permit, task, key)
        raise SimulatedCrashError(key)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)


@pytest.fixture
def world(uow: Callable[[], SqlUnitOfWork]) -> World:
    return World(uow)


def crash(world: World, after_command: bool) -> int:
    real = world.actuator
    world.build_services(CrashingActuator(real, after_command))
    with pytest.raises(SimulatedCrashError):
        world.proposals.propose(world.action())
    world.build_services(real)
    [request] = world.events(EventKind.EXECUTION_REQUESTED)
    assert request.task_id is not None
    return request.task_id


def reconcile(world: World) -> Any:
    return reconcile_executions(world.uow, world.clock, world.actuator, MESSAGES)


def test_the_request_is_durable_before_the_valve_and_closed_with_the_same_key(world: World) -> None:
    result = world.proposals.propose(world.action())

    [request] = world.events(EventKind.EXECUTION_REQUESTED, result.task.id)
    [execution] = world.events(EventKind.EXECUTION, result.task.id)
    assert (
        request.idempotency_key == execution.idempotency_key == f"task-{result.task.id}:attempt-1"
    )
    assert (request.id or 0) < (execution.id or 0)
    assert execution.inputs["target_mm"] == 15.0
    assert execution.inputs["rate_mm_per_h"] == RATE


def test_a_crash_after_the_command_leaves_an_open_request(world: World) -> None:
    task_id = crash(world, after_command=True)

    assert world.task(task_id).status is TaskStatus.SCHEDULED
    with world.uow() as u:
        assert [e.task_id for e in u.events.find_unclosed_execution_requests()] == [task_id]


def test_reconciliation_closes_a_recorded_command_without_running_it_again(world: World) -> None:
    task_id = crash(world, after_command=True)

    report = reconcile(world)

    assert report.closed_as_executed == (task_id,)
    assert world.task(task_id).status is TaskStatus.EXECUTED
    [execution] = world.events(EventKind.EXECUTION, task_id)
    assert execution.inputs["reconciled"] is True
    assert world.valve_open()  # the one run that was started; a second open would fail
    assert world.due.run_due(world.clock.now() + timedelta(days=1)) == []


def test_reconciliation_fails_an_unknown_command_and_never_runs_it(world: World) -> None:
    task_id = crash(world, after_command=False)

    report = reconcile(world)

    assert report.failed == (task_id,)
    assert world.task(task_id).status is TaskStatus.FAILED
    [failure] = world.events(EventKind.EXECUTION_FAILED, task_id)
    assert failure.idempotency_key == f"task-{task_id}:attempt-1"
    assert not world.valve_open()
    with world.uow() as u:
        [notification] = u.notifications.list()
    assert "no se confirmó tras un reinicio" in notification.message
    assert "No se reintentará" in notification.message


def test_after_a_restart_an_applied_command_is_failed_not_repeated(world: World) -> None:
    task_id = crash(world, after_command=True)
    world.build_services()  # new process: actuator records are gone (D014)

    report = reconcile(world)

    assert report.failed == (task_id,)
    assert not world.valve_open()  # the new simulator never opened anything


def test_reconciliation_is_idempotent(world: World) -> None:
    crash(world, after_command=False)
    reconcile(world)

    second = reconcile(world)

    assert (second.closed_as_executed, second.failed) == ((), ())
    assert len(world.events(EventKind.EXECUTION_FAILED)) == 1


def test_the_report_says_the_simulator_was_not_resumed(world: World) -> None:
    assert reconcile(world).simulator_state_resumed is False


def test_an_actuator_refusal_fails_the_task_with_the_same_key(world: World) -> None:
    from app.actuation.simulated import SimulatedActuator

    world.build_services(
        SimulatedActuator(world.valves, FakeEmergencyStop(True), world.clock, RATE)
    )

    result = world.proposals.propose(world.action())

    assert result.task.status is TaskStatus.FAILED
    [failure] = world.events(EventKind.EXECUTION_FAILED, result.task.id)
    assert failure.idempotency_key == f"task-{result.task.id}:attempt-1"
    assert not world.valve_open()
