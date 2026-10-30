"""The farmer's decision on a held task, with the real gate and actuator (D008, D062)."""

from collections.abc import Callable
from datetime import timedelta

import pytest

from app.domain.enums import ActionType, AutonomyLevel, EventKind, TaskStatus
from app.domain.errors import InvalidTransitionError
from app.domain.models import Reading
from app.persistence.unit_of_work import SqlUnitOfWork
from app.services.approvals import ApprovalService
from app.services.control import EmergencyStopService
from tests.integration.services.world import DAY1, World

UowFactory = Callable[[], SqlUnitOfWork]


def _approvals(world: World) -> ApprovalService:
    return ApprovalService(world.uow, world.clock, world.due)


def _held_for_rain(world: World, at_hours: float = 0) -> int:
    world.forecast.mm = 8.0
    result = world.proposals.propose(world.action(at=DAY1 + timedelta(hours=at_hours)))
    assert result.task.status is TaskStatus.PENDING_APPROVAL
    assert result.task.id is not None
    return result.task.id


def test_an_approved_irrigation_held_for_rain_executes(uow: UowFactory) -> None:
    """D062 required test."""
    world = World(uow)
    task_id = _held_for_rain(world)

    task = _approvals(world).approve(task_id, "farmer")

    assert task.status is TaskStatus.EXECUTED
    assert world.valve_open()
    [approval] = world.events(EventKind.APPROVAL, task_id=task_id)
    assert approval.actor == "farmer"
    assert approval.inputs == {"approved_codes": ["rain_forecast_above_limit"]}
    [requested] = world.events(EventKind.EXECUTION_REQUESTED, task_id=task_id)
    assert requested.autonomy_level is AutonomyLevel.APPROVAL


def test_an_approval_does_not_override_the_emergency_stop(uow: UowFactory) -> None:
    """D062 required test: the stop is checked again and never approved away."""
    world = World(uow)
    task_id = _held_for_rain(world)
    world.set_emergency_stop(True)

    task = _approvals(world).approve(task_id, "farmer")

    assert task.status is TaskStatus.FAILED
    assert not world.valve_open()
    assert world.events(EventKind.EXECUTION, task_id=task_id) == []
    [failed] = world.events(EventKind.EXECUTION_FAILED, task_id=task_id)
    assert "emergency_stop_active" in failed.reason
    assert "rain_forecast_above_limit" not in failed.reason  # only what blocked it


def test_a_new_violation_before_it_is_due_fails_the_approved_task(uow: UowFactory) -> None:
    """D062 required test: the farmer approved the rain risk, not a soaked field."""
    world = World(uow)
    later = _held_for_rain(world, at_hours=3)
    assert _approvals(world).approve(later, "farmer").status is TaskStatus.SCHEDULED
    world.clock.advance(timedelta(hours=3))
    _soil_reads(world, 30.0)  # 94 % of field capacity, above the 85 % limit

    [task] = world.due.run_due(world.clock.now())

    assert task.id == later and task.status is TaskStatus.FAILED
    [failed] = world.events(EventKind.EXECUTION_FAILED, task_id=later)
    assert "moisture_above_limit" in failed.reason
    assert "rain_forecast_above_limit" not in failed.reason  # that one was approved
    assert world.events(EventKind.EXECUTION, task_id=later) == []


def _soil_reads(world: World, vwc: float) -> None:
    with world.uow() as u:
        [sensor] = u.sensors.list_by_zone(world.zone_id)
        assert sensor.id is not None
        u.readings.add_many([Reading(sensor.id, vwc, world.clock.now())])
        u.commit()


def test_an_approved_task_for_later_waits_until_it_is_due(uow: UowFactory) -> None:
    world = World(uow)
    task_id = _held_for_rain(world, at_hours=3)

    task = _approvals(world).approve(task_id, "farmer")
    world.clock.advance(timedelta(hours=3))
    [executed] = world.due.run_due(world.clock.now())

    assert task.status is TaskStatus.SCHEDULED
    assert executed.status is TaskStatus.EXECUTED


def test_a_type_without_actuator_command_stays_scheduled_as_manual_work(
    uow: UowFactory,
) -> None:
    world = World(uow)
    fertilizer = world.proposals.propose(
        world.action(ActionType.FERTILIZER, params={"product": "urea", "n_kg_ha": 60.0})
    )
    assert fertilizer.task.id is not None

    task = _approvals(world).approve(fertilizer.task.id, "farmer")

    assert task.status is TaskStatus.SCHEDULED
    assert world.events(EventKind.EXECUTION_REQUESTED, task_id=task.id) == []


def test_a_rejection_is_final_and_logged_with_its_reason(uow: UowFactory) -> None:
    world = World(uow)
    task_id = _held_for_rain(world)

    task = _approvals(world).reject(task_id, "farmer", "Prefiero esperar la lluvia")

    assert task.status is TaskStatus.REJECTED
    [rejection] = world.events(EventKind.REJECTION, task_id=task_id)
    assert rejection.reason == "Rejected by the farmer: Prefiero esperar la lluvia"
    with pytest.raises(InvalidTransitionError):
        _approvals(world).approve(task_id, "farmer")


def test_only_a_held_task_can_be_approved(uow: UowFactory) -> None:
    world = World(uow)
    executed = world.proposals.propose(world.action())
    assert executed.task.id is not None

    with pytest.raises(InvalidTransitionError):
        _approvals(world).approve(executed.task.id, "farmer")


def test_the_emergency_stop_switch_is_logged_once_per_change(uow: UowFactory) -> None:
    world = World(uow)
    service = EmergencyStopService(uow, world.clock)

    on = service.set(True, "farmer")
    again = service.set(True, "farmer")
    off = service.set(False, "farmer")

    assert (on.emergency_stop_active, again.emergency_stop_active) == (True, True)
    assert off.emergency_stop_active is False
    reasons = [e.reason for e in world.events(EventKind.EMERGENCY_STOP)]
    assert reasons == ["Emergency stop activated.", "Emergency stop released."]
    assert service.state().changed_by == "farmer"
