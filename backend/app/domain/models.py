"""Domain entities and value objects.

Plain frozen dataclasses with no persistence concerns. `id` is None until the
entity is stored. Every datetime is timezone-aware UTC.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime

from app.domain.enums import (
    ActionType,
    AutonomyLevel,
    CycleStatus,
    EventKind,
    GateOutcome,
    SensorKind,
    TaskStatus,
)

JsonValue = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject = Mapping[str, JsonValue]


@dataclass(frozen=True)
class Money:
    """An amount in minor units (e.g. cents) to avoid float rounding."""

    amount_minor: int
    currency: str


@dataclass(frozen=True)
class Plot:
    name: str
    latitude: float
    longitude: float
    area_ha: float
    created_at: datetime
    utc_offset_hours: float  # defines the plot's local calendar day (D018)
    id: int | None = None


@dataclass(frozen=True)
class Zone:
    plot_id: int
    name: str
    area_ha: float
    field_capacity_pct: float
    valve_id: str
    id: int | None = None

    @property
    def area_m2(self) -> float:
        """Zone area in square metres (1 mm over 1 m2 is 1 litre)."""
        return self.area_ha * 10_000


@dataclass(frozen=True)
class Sensor:
    zone_id: int
    kind: SensorKind
    unit: str
    id: int | None = None


@dataclass(frozen=True)
class Reading:
    sensor_id: int
    value: float
    recorded_at: datetime
    id: int | None = None


@dataclass(frozen=True)
class CropCycle:
    plot_id: int
    crop: str
    sowing_date: date
    accumulated_gdd: float = 0.0
    gdd_updated_through: date | None = None  # last local day counted (idempotency)
    status: CycleStatus = CycleStatus.ACTIVE
    id: int | None = None


@dataclass(frozen=True)
class Stage:
    cycle_id: int
    name: str
    started_at: datetime
    gdd_at_start: float
    ended_at: datetime | None = None
    id: int | None = None


@dataclass(frozen=True)
class Task:
    cycle_id: int
    action_type: ActionType
    scheduled_for: datetime
    status: TaskStatus
    effective_level: AutonomyLevel
    rationale: str
    created_at: datetime
    updated_at: datetime
    zone_id: int | None = None
    params: JsonObject = field(default_factory=dict)
    estimated_cost: Money | None = None
    revert_deadline: datetime | None = None
    id: int | None = None


@dataclass(frozen=True)
class Decision:
    task_id: int
    requested_level: AutonomyLevel
    effective_level: AutonomyLevel
    outcome: GateOutcome
    reason: str
    created_at: datetime
    violations: tuple[JsonObject, ...] = ()
    inputs: JsonObject = field(default_factory=dict)
    id: int | None = None


@dataclass(frozen=True)
class Event:
    """An entry of the append-only event log."""

    kind: EventKind
    actor: str
    reason: str
    occurred_at: datetime
    task_id: int | None = None
    decision_id: int | None = None
    autonomy_level: AutonomyLevel | None = None
    rule: str | None = None
    inputs: JsonObject = field(default_factory=dict)
    idempotency_key: str | None = None
    id: int | None = None


@dataclass(frozen=True)
class Notification:
    message: str
    created_at: datetime
    task_id: int | None = None
    read_at: datetime | None = None
    revert_deadline: datetime | None = None
    id: int | None = None


@dataclass(frozen=True)
class Report:
    cycle_id: int
    language: str
    content: str
    created_at: datetime
    stage_id: int | None = None
    id: int | None = None


@dataclass(frozen=True)
class ControlState:
    """Global runtime switches, persisted so no global mutable state exists."""

    emergency_stop_active: bool
    changed_at: datetime | None = None
    changed_by: str | None = None


@dataclass(frozen=True)
class SimClockState:
    """Persisted anchor of the simulated clock (logic arrives in step 3).

    Simulated now = `sim_anchor + (wall_now - wall_anchor) * speed_factor`,
    or `sim_anchor` while paused.
    """

    sim_anchor: datetime
    wall_anchor: datetime
    speed_factor: float
    paused: bool
