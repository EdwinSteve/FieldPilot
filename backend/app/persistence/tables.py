"""SQLModel table definitions. Only the persistence package imports these.

The schema is created with `create_all` and reset on every schema change;
there are no migrations during the hackathon (D012).
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.persistence.types import UTCDateTime


def _utc(*, nullable: bool = False, index: bool = False) -> Any:
    return Field(sa_column=Column(UTCDateTime(), nullable=nullable, index=index))


def _json(default: Any) -> Any:
    return Field(default_factory=default, sa_column=Column(JSON, nullable=False))


class PlotRow(SQLModel, table=True):
    __tablename__ = "plot"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    latitude: float
    longitude: float
    area_ha: float
    created_at: datetime = _utc()
    utc_offset_hours: float


class ZoneRow(SQLModel, table=True):
    __tablename__ = "zone"

    id: int | None = Field(default=None, primary_key=True)
    plot_id: int = Field(foreign_key="plot.id", index=True)
    name: str
    area_ha: float
    field_capacity_pct: float
    valve_id: str


class SensorRow(SQLModel, table=True):
    __tablename__ = "sensor"

    id: int | None = Field(default=None, primary_key=True)
    zone_id: int = Field(foreign_key="zone.id", index=True)
    kind: str
    unit: str


class ReadingRow(SQLModel, table=True):
    __tablename__ = "reading"

    id: int | None = Field(default=None, primary_key=True)
    sensor_id: int = Field(foreign_key="sensor.id", index=True)
    value: float
    recorded_at: datetime = _utc(index=True)


class CropCycleRow(SQLModel, table=True):
    __tablename__ = "crop_cycle"

    id: int | None = Field(default=None, primary_key=True)
    plot_id: int = Field(foreign_key="plot.id", index=True)
    crop: str
    sowing_date: date
    accumulated_gdd: float
    gdd_updated_through: date | None = None
    status: str


class StageRow(SQLModel, table=True):
    __tablename__ = "stage"

    id: int | None = Field(default=None, primary_key=True)
    cycle_id: int = Field(foreign_key="crop_cycle.id", index=True)
    name: str
    started_at: datetime = _utc()
    ended_at: datetime | None = _utc(nullable=True)
    gdd_at_start: float


class TaskRow(SQLModel, table=True):
    __tablename__ = "task"

    id: int | None = Field(default=None, primary_key=True)
    cycle_id: int = Field(foreign_key="crop_cycle.id", index=True)
    zone_id: int | None = Field(default=None, foreign_key="zone.id")
    action_type: str
    params: dict[str, Any] = _json(dict)
    scheduled_for: datetime = _utc(index=True)
    status: str = Field(index=True)
    effective_level: str
    rationale: str
    estimated_cost_minor: int | None = None
    estimated_cost_currency: str | None = None
    revert_deadline: datetime | None = _utc(nullable=True)
    created_at: datetime = _utc()
    updated_at: datetime = _utc()


class DecisionRow(SQLModel, table=True):
    __tablename__ = "decision"

    id: int | None = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id", index=True)
    requested_level: str
    effective_level: str
    outcome: str
    violations: list[dict[str, Any]] = _json(list)
    reason: str
    inputs: dict[str, Any] = _json(dict)
    created_at: datetime = _utc()


class EventRow(SQLModel, table=True):
    __tablename__ = "event"
    # One EXECUTION_REQUESTED (or closing event) per key; NULL keys are not unique.
    __table_args__ = (UniqueConstraint("kind", "idempotency_key"),)

    id: int | None = Field(default=None, primary_key=True)
    occurred_at: datetime = _utc(index=True)
    kind: str = Field(index=True)
    actor: str
    task_id: int | None = Field(default=None, foreign_key="task.id", index=True)
    decision_id: int | None = Field(default=None, foreign_key="decision.id")
    autonomy_level: str | None = None
    rule: str | None = None
    reason: str
    inputs: dict[str, Any] = _json(dict)
    idempotency_key: str | None = Field(default=None, index=True)


class NotificationRow(SQLModel, table=True):
    __tablename__ = "notification"

    id: int | None = Field(default=None, primary_key=True)
    task_id: int | None = Field(default=None, foreign_key="task.id")
    message: str
    created_at: datetime = _utc()
    read_at: datetime | None = _utc(nullable=True)
    revert_deadline: datetime | None = _utc(nullable=True)


class ReportRow(SQLModel, table=True):
    __tablename__ = "report"

    id: int | None = Field(default=None, primary_key=True)
    cycle_id: int = Field(foreign_key="crop_cycle.id", index=True)
    stage_id: int | None = Field(default=None, foreign_key="stage.id")
    language: str
    content: str
    created_at: datetime = _utc()


class ControlStateRow(SQLModel, table=True):
    __tablename__ = "control_state"

    id: int = Field(default=1, primary_key=True)
    emergency_stop_active: bool = False
    changed_at: datetime | None = _utc(nullable=True)
    changed_by: str | None = None


class SimClockStateRow(SQLModel, table=True):
    __tablename__ = "sim_clock_state"

    id: int = Field(default=1, primary_key=True)
    sim_anchor: datetime = _utc()
    wall_anchor: datetime = _utc()
    speed_factor: float
    paused: bool
