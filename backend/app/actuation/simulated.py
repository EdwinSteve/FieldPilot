"""Simulated actuator: turns gate-issued permits into valve commands.

It only executes. Deciding, logging and reverting belong to the services
(architecture §4.3, §4.4). Its records live in memory, like the simulator
(D014), so after a restart `lookup` finds nothing and D013 resolves it.
"""

from collections.abc import Mapping
from datetime import datetime

from app.actuation.ports import EmergencyStopState, ExecutionResult
from app.autonomy.gate import ExecutionPermit
from app.domain.enums import ActionType
from app.domain.errors import (
    EmergencyStopActiveError,
    NotFoundError,
    PermitMismatchError,
    UnsupportedActionError,
    ValveError,
)
from app.domain.models import JsonValue, Task
from app.safety.rules import IRRIGATION_ACTIONS
from app.simulator.clock import Clock
from app.simulator.ports import ValveController

# Action types this actuator can run (architecture §4.4, D034).
SUPPORTED_ACTIONS = IRRIGATION_ACTIONS | {ActionType.STOP_IRRIGATION}


class SimulatedActuator:
    """Drives valves through `ValveController` only (architecture §4.6)."""

    def __init__(
        self,
        valves: ValveController,
        emergency_stop: EmergencyStopState,
        clock: Clock,
        rate_mm_per_h: float,
    ) -> None:
        if rate_mm_per_h <= 0:
            raise ValueError("irrigation rate must be positive")
        self._valves = valves
        self._emergency_stop = emergency_stop
        self._clock = clock
        self._rate_mm_per_h = rate_mm_per_h
        self._records: dict[str, ExecutionResult] = {}
        self._latest_run_by_zone: dict[int, str] = {}

    def execute(self, permit: ExecutionPermit, task: Task, idempotency_key: str) -> ExecutionResult:
        """Run the permitted action once per key; a repeated key returns the first result."""
        if not isinstance(permit, ExecutionPermit):
            raise PermissionError("the actuator only accepts a gate-issued ExecutionPermit")
        _ensure_matches(permit, task)
        recorded = self._records.get(idempotency_key)
        if recorded is not None:
            return recorded
        at = self._clock.now()
        if permit.action_type in IRRIGATION_ACTIONS:
            result = self._irrigate(permit, idempotency_key, at)
        elif permit.action_type is ActionType.STOP_IRRIGATION:
            result = self._stop(permit, idempotency_key, at)
        else:
            raise UnsupportedActionError(f"no actuator command for {permit.action_type}")
        self._records[idempotency_key] = result
        return result

    def lookup(self, idempotency_key: str) -> ExecutionResult | None:
        return self._records.get(idempotency_key)

    def interrupt(self, idempotency_key: str, at: datetime) -> float | None:
        """Close the run started under this key if it is still flowing; mm applied, or None."""
        record = self._records.get(idempotency_key)
        if record is None or record.zone_id is None or record.action_type not in IRRIGATION_ACTIONS:
            return None
        if self._latest_run_by_zone.get(record.zone_id) != idempotency_key:
            return None  # a later run owns the valve now
        if not self._valves.status(record.zone_id, at).is_open:
            return None
        return self._valves.close(record.zone_id, at)

    def close_valve(self, zone_id: int, at: datetime) -> float | None:
        """Close the zone's valve. Always allowed, even during an emergency stop (D022)."""
        try:
            return self._valves.close(zone_id, at)
        except (ValveError, NotFoundError):
            return None  # already closed, or unknown to a freshly started simulator

    def _irrigate(self, permit: ExecutionPermit, key: str, at: datetime) -> ExecutionResult:
        if self._emergency_stop.is_active():
            raise EmergencyStopActiveError("emergency stop active: no valve may open")
        zone_id = _require_zone(permit)
        target_mm = _volume_mm(permit)
        self._valves.open(zone_id, target_mm, self._rate_mm_per_h, at)
        self._latest_run_by_zone[zone_id] = key
        return ExecutionResult(key, permit.action_type, zone_id, at, target_mm, self._rate_mm_per_h)

    def _stop(self, permit: ExecutionPermit, key: str, at: datetime) -> ExecutionResult:
        zone_id = _require_zone(permit)
        applied = self.close_valve(zone_id, at)
        return ExecutionResult(
            key, permit.action_type, zone_id, at, 0.0, self._rate_mm_per_h, applied_mm=applied
        )


def _ensure_matches(permit: ExecutionPermit, task: Task) -> None:
    if (
        permit.action_type is not task.action_type
        or permit.zone_id != task.zone_id
        or _normalized(permit.params) != _normalized(task.params)
    ):
        raise PermitMismatchError(f"permit {permit.proposal_key} does not match task {task.id}")


def _normalized(params: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    """Compare 15 and 15.0 as equal; JSON storage may return either."""
    return {
        name: float(value) if isinstance(value, int) and not isinstance(value, bool) else value
        for name, value in params.items()
    }


def _require_zone(permit: ExecutionPermit) -> int:
    if permit.zone_id is None:
        raise PermitMismatchError(f"{permit.action_type} needs a zone")
    return permit.zone_id


def _volume_mm(permit: ExecutionPermit) -> float:
    value = permit.params.get("volume_mm")
    if not isinstance(value, int | float) or isinstance(value, bool) or value <= 0:
        raise PermitMismatchError("irrigation needs a positive volume_mm")
    return float(value)
