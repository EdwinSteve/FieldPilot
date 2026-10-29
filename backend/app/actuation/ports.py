"""Actuation interfaces. Services depend on these, never on the simulator."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.autonomy.gate import ExecutionPermit
from app.domain.enums import ActionType
from app.domain.models import Task


@dataclass(frozen=True)
class ExecutionResult:
    """What the actuator did for one idempotency key."""

    idempotency_key: str
    action_type: ActionType
    zone_id: int | None
    started_at: datetime
    target_mm: float  # requested; 0 for stop_irrigation
    rate_mm_per_h: float  # D038
    applied_mm: float | None = None  # stop_irrigation: mm the closed run had applied


class EmergencyStopState(Protocol):
    def is_active(self) -> bool: ...


class Actuator(Protocol):
    def execute(
        self, permit: ExecutionPermit, task: Task, idempotency_key: str
    ) -> ExecutionResult: ...
    def lookup(self, idempotency_key: str) -> ExecutionResult | None: ...
    def interrupt(self, idempotency_key: str, at: datetime) -> float | None: ...
    def close_valve(self, zone_id: int, at: datetime) -> float | None: ...
