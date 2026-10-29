"""SimulatedActuator: permits only, never twice per key, never opens during a stop."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from app.actuation.simulated import SimulatedActuator
from app.autonomy.gate import AutonomyGate, ExecutionPermit, GateContext
from app.autonomy.policy import load_autonomy_policy
from app.domain.enums import ActionType, AutonomyLevel, TaskStatus
from app.domain.errors import (
    EmergencyStopActiveError,
    PermitMismatchError,
    UnsupportedActionError,
)
from app.domain.models import Task
from app.domain.proposals import ParamValue
from app.simulator.field import FieldSimulator
from app.simulator.water_balance import SoilParams
from tests.builders import LIMITS, SAFE, proposal
from tests.conftest import CONFIG_DIR
from tests.fakes import FakeClock, FakeEmergencyStop

T0 = datetime(2026, 10, 28, 6, 0, tzinfo=UTC)
ZONE = 2
RATE = 6.0  # mm/h, as in config/actuation.yaml
KEY = "task-1:attempt-1"
GATE = AutonomyGate(load_autonomy_policy(CONFIG_DIR / "autonomy.yaml"), LIMITS)


class Rig:
    def __init__(self) -> None:
        self.clock = FakeClock(T0)
        self.stop = FakeEmergencyStop()
        self.valves = FieldSimulator(start=T0)
        self.valves.add_zone(ZONE, SoilParams(), initial_vwc=20.0)
        self.actuator = SimulatedActuator(self.valves, self.stop, self.clock, RATE)

    def is_open(self) -> bool:
        return self.valves.status(ZONE, self.clock.now()).is_open


@pytest.fixture
def rig() -> Rig:
    return Rig()


def permit_for(
    action_type: ActionType = ActionType.IRRIGATION,
    params: dict[str, ParamValue] | None = None,
) -> ExecutionPermit:
    auth = GATE.authorize(proposal(action_type, params, zone_id=ZONE), GateContext(SAFE, None))
    assert auth.permit is not None, auth.verdict
    return auth.permit


def task_for(permit: ExecutionPermit, **changes: Any) -> Task:
    fields: dict[str, Any] = {
        "cycle_id": 1,
        "action_type": permit.action_type,
        "scheduled_for": T0,
        "status": TaskStatus.SCHEDULED,
        "effective_level": AutonomyLevel.AUTONOMOUS,
        "rationale": "test",
        "created_at": T0,
        "updated_at": T0,
        "zone_id": permit.zone_id,
        "params": {"volume_mm": 15} if "volume_mm" in permit.params else {},
        "id": 1,
    }
    fields.update(changes)
    return Task(**fields)


# --- permits --------------------------------------------------------------


def test_a_raw_action_is_refused_and_no_valve_opens(rig: Rig) -> None:
    raw_action = cast("Any", proposal(zone_id=ZONE))
    permit = permit_for()

    with pytest.raises(PermissionError, match="gate-issued ExecutionPermit"):
        rig.actuator.execute(raw_action, task_for(permit), KEY)
    assert not rig.is_open()


@pytest.mark.parametrize(
    "change",
    [
        {"zone_id": 3},
        {"params": {"volume_mm": 20}},
        {"action_type": ActionType.EXTRA_IRRIGATION},
    ],
)
def test_a_permit_for_another_action_is_refused(rig: Rig, change: dict[str, Any]) -> None:
    permit = permit_for()

    with pytest.raises(PermitMismatchError):
        rig.actuator.execute(permit, task_for(permit, **change), KEY)
    assert not rig.is_open()


def test_the_same_key_never_opens_the_valve_twice(rig: Rig) -> None:
    permit = permit_for()
    first = rig.actuator.execute(permit, task_for(permit), KEY)
    rig.clock.advance(timedelta(hours=3))  # first run finished; a second open would succeed

    again = rig.actuator.execute(permit, task_for(permit), KEY)

    assert again == first
    assert not rig.is_open()
    assert rig.actuator.lookup(KEY) == first


def test_lookup_of_an_unknown_key_finds_nothing(rig: Rig) -> None:
    assert rig.actuator.lookup("task-9:attempt-1") is None


# --- emergency stop (D022) ------------------------------------------------


@pytest.mark.parametrize("action_type", [ActionType.IRRIGATION, ActionType.EXTRA_IRRIGATION])
def test_no_valve_opens_during_an_emergency_stop(rig: Rig, action_type: ActionType) -> None:
    permit = permit_for(action_type, {"volume_mm": 5.0})
    rig.stop.active = True

    with pytest.raises(EmergencyStopActiveError):
        rig.actuator.execute(permit, task_for(permit, params={"volume_mm": 5.0}), KEY)
    assert not rig.is_open()
    assert rig.actuator.lookup(KEY) is None


def test_stop_irrigation_closes_the_valve_during_an_emergency_stop(rig: Rig) -> None:
    irrigation = permit_for()
    rig.actuator.execute(irrigation, task_for(irrigation), KEY)
    rig.clock.advance(timedelta(minutes=30))
    rig.stop.active = True
    stop = permit_for(ActionType.STOP_IRRIGATION, {})

    result = rig.actuator.execute(stop, task_for(stop, id=2), "task-2:attempt-1")

    assert not rig.is_open()
    assert result.applied_mm == 3.0  # 6 mm/h x 0.5 h


def test_close_valve_is_allowed_during_an_emergency_stop(rig: Rig) -> None:
    permit = permit_for()
    rig.actuator.execute(permit, task_for(permit), KEY)
    rig.stop.active = True
    rig.clock.advance(timedelta(minutes=10))

    assert rig.actuator.close_valve(ZONE, rig.clock.now()) == 1.0
    assert not rig.is_open()


def test_close_valve_on_a_closed_or_unknown_valve_reports_nothing(rig: Rig) -> None:
    assert rig.actuator.close_valve(ZONE, T0) is None
    assert rig.actuator.close_valve(99, T0) is None


# --- applied water (D007) -------------------------------------------------


def test_interrupting_mid_irrigation_returns_rate_times_elapsed(rig: Rig) -> None:
    permit = permit_for()
    rig.actuator.execute(permit, task_for(permit), KEY)
    rig.clock.advance(timedelta(hours=1, minutes=30))

    applied = rig.actuator.interrupt(KEY, rig.clock.now())

    assert applied == 9.0  # exact: 6 mm/h x 1.5 h
    assert not rig.is_open()


def test_a_finished_irrigation_cannot_be_interrupted_and_never_exceeds_target(rig: Rig) -> None:
    permit = permit_for()
    rig.actuator.execute(permit, task_for(permit), KEY)
    rig.clock.advance(timedelta(hours=4))  # 15 mm at 6 mm/h ends after 2.5 h

    assert rig.actuator.interrupt(KEY, rig.clock.now()) is None
    assert rig.valves.status(ZONE, rig.clock.now()).applied_mm == 15.0


def test_interrupt_ignores_a_key_whose_valve_now_belongs_to_a_later_run(rig: Rig) -> None:
    first = permit_for()
    rig.actuator.execute(first, task_for(first), KEY)
    rig.clock.advance(timedelta(hours=3))
    second = permit_for(ActionType.IRRIGATION, {"volume_mm": 10.0})
    rig.actuator.execute(second, task_for(second, params={"volume_mm": 10}), "task-2:attempt-1")

    assert rig.actuator.interrupt(KEY, rig.clock.now()) is None
    assert rig.is_open()


def test_interrupt_of_an_unknown_key_does_nothing(rig: Rig) -> None:
    assert rig.actuator.interrupt("task-9:attempt-1", T0) is None


def test_result_records_target_rate_and_start(rig: Rig) -> None:
    permit = permit_for()

    result = rig.actuator.execute(permit, task_for(permit), KEY)

    assert (result.target_mm, result.rate_mm_per_h, result.started_at) == (15.0, RATE, T0)
    assert result.zone_id == ZONE and result.idempotency_key == KEY


# --- unsupported types ----------------------------------------------------


def test_calendar_shift_is_not_executed_yet(rig: Rig) -> None:
    permit = permit_for(ActionType.CALENDAR_SHIFT, {"shift_days": 1.0})

    with pytest.raises(UnsupportedActionError, match="calendar_shift"):
        rig.actuator.execute(permit, task_for(permit, params={"shift_days": 1.0}), KEY)


def test_rate_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        SimulatedActuator(FieldSimulator(start=T0), FakeEmergencyStop(), FakeClock(T0), 0.0)
