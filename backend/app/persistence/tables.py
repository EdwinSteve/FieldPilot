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
    municipality: str = ""
    department: str = ""


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
    automated: bool = True
    own_risk: bool = False
    plan_model: str | None = None
    plan_rank: int | None = None
    plan_rel_yield_p50: float | None = None
    plan_p_success: float | None = None
    harvested_on: date | None = None


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


# Identity (§4.12, D082). Wall-clock datetimes, never the simulated clock.


class UserRow(SQLModel, table=True):
    __tablename__ = "user"

    id: int | None = Field(default=None, primary_key=True)
    phone: str = Field(unique=True, index=True)
    full_name: str
    role: str
    password_hash: str
    active: bool = True
    failed_logins: int = 0
    locked_until: datetime | None = _utc(nullable=True)
    last_login_at: datetime | None = _utc(nullable=True)
    consent_version: str
    consent_at: datetime = _utc()
    created_at: datetime = _utc()


class RefreshSessionRow(SQLModel, table=True):
    __tablename__ = "refresh_session"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    token_hash: str = Field(unique=True, index=True)
    family_id: str = Field(index=True)
    expires_at: datetime = _utc()
    created_at: datetime = _utc()
    used_at: datetime | None = _utc(nullable=True)
    revoked_at: datetime | None = _utc(nullable=True)


class AuthEventRow(SQLModel, table=True):
    __tablename__ = "auth_event"

    id: int | None = Field(default=None, primary_key=True)
    occurred_at: datetime = _utc(index=True)
    kind: str = Field(index=True)
    user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    detail: dict[str, Any] = _json(dict)


class PlotMemberRow(SQLModel, table=True):
    __tablename__ = "plot_member"
    __table_args__ = (UniqueConstraint("plot_id", "user_id"),)

    id: int | None = Field(default=None, primary_key=True)
    plot_id: int = Field(foreign_key="plot.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)


# Plots, lots and their trace (§4.13, §4.14, D083).


class PlotSiteRow(SQLModel, table=True):
    """The site snapshot job of a plot; `ready` is read from the snapshot file itself."""

    __tablename__ = "plot_site"

    plot_id: int = Field(foreign_key="plot.id", primary_key=True)
    status: str
    requested_at: datetime = _utc()
    finished_at: datetime | None = _utc(nullable=True)
    message: str | None = None


class HarvestLotRow(SQLModel, table=True):
    __tablename__ = "harvest_lot"

    code: str = Field(primary_key=True)
    cycle_id: int = Field(foreign_key="crop_cycle.id", unique=True)
    plot_id: int = Field(foreign_key="plot.id", index=True)
    crop: str
    harvested_on: date
    quantity_g: int
    grade: str
    created_at: datetime = _utc()


class TraceEventRow(SQLModel, table=True):
    __tablename__ = "trace_event"
    __table_args__ = (UniqueConstraint("lot_code", "seq"),)

    id: int | None = Field(default=None, primary_key=True)
    lot_code: str = Field(foreign_key="harvest_lot.code", index=True)
    seq: int
    biz_step: str
    occurred_at: datetime = _utc()
    actor: str
    quantity_g: int
    data: dict[str, Any] = _json(dict)
    prev_hash: str
    hash: str


# The market (§4.15, D085). Grams and minor units; customer data never in `event`.


class WarehouseRow(SQLModel, table=True):
    __tablename__ = "warehouse"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True)
    name: str
    municipality: str
    department: str
    cold_storage: bool


class ListingRow(SQLModel, table=True):
    __tablename__ = "listing"

    id: int | None = Field(default=None, primary_key=True)
    lot_code: str = Field(foreign_key="harvest_lot.code", unique=True)
    farmer_id: int = Field(foreign_key="user.id", index=True)
    warehouse_id: int = Field(foreign_key="warehouse.id", index=True)
    crop: str = Field(index=True)
    quantity_g: int
    farmer_price_minor: int
    currency: str
    status: str = Field(index=True)
    created_at: datetime = _utc()


class ShipmentRow(SQLModel, table=True):
    __tablename__ = "shipment"

    id: int | None = Field(default=None, primary_key=True)
    listing_id: int = Field(foreign_key="listing.id", unique=True)
    warehouse_id: int = Field(foreign_key="warehouse.id")
    dispatched_g: int
    dispatched_at: datetime = _utc()
    received_g: int | None = None
    temperature_c: float | None = None
    received_at: datetime | None = _utc(nullable=True)
    received_by: str | None = None


class StockMovementRow(SQLModel, table=True):
    __tablename__ = "stock_movement"

    id: int | None = Field(default=None, primary_key=True)
    listing_id: int = Field(foreign_key="listing.id", index=True)
    delta_g: int
    reason: str
    ref: str
    occurred_at: datetime = _utc()


class OfferRow(SQLModel, table=True):
    __tablename__ = "offer"

    id: int | None = Field(default=None, primary_key=True)
    listing_id: int = Field(foreign_key="listing.id", index=True)
    discount_pct: int
    starts_on: date
    ends_on: date
    created_at: datetime = _utc()


class CustomerProfileRow(SQLModel, table=True):
    __tablename__ = "customer_profile"

    user_id: int = Field(foreign_key="user.id", primary_key=True)
    delivery_address: str | None = None
    consent_profiling_at: datetime | None = _utc(nullable=True)


class CartItemRow(SQLModel, table=True):
    __tablename__ = "cart_item"
    __table_args__ = (UniqueConstraint("customer_id", "listing_id"),)

    id: int | None = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="user.id", index=True)
    listing_id: int = Field(foreign_key="listing.id")
    quantity_kg: int


class CustomerOrderRow(SQLModel, table=True):
    __tablename__ = "customer_order"

    id: int | None = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="user.id", index=True)
    status: str = Field(index=True)
    total_minor: int
    currency: str
    payment_ref: str
    delivery_address: str
    placed_at: datetime = _utc(index=True)
    delivered_at: datetime | None = _utc(nullable=True)
    cancelled_at: datetime | None = _utc(nullable=True)


class OrderLineRow(SQLModel, table=True):
    __tablename__ = "order_line"

    id: int | None = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="customer_order.id", index=True)
    listing_id: int = Field(foreign_key="listing.id", index=True)
    lot_code: str = Field(foreign_key="harvest_lot.code")
    farmer_id: int = Field(foreign_key="user.id", index=True)
    crop: str
    quantity_kg: int
    farmer_minor: int  # per kg, frozen at checkout
    logistics_minor: int
    platform_minor: int
    discount_pct: int
    currency: str


class PayoutRow(SQLModel, table=True):
    __tablename__ = "payout"

    id: int | None = Field(default=None, primary_key=True)
    order_line_id: int = Field(foreign_key="order_line.id", unique=True)
    farmer_id: int = Field(foreign_key="user.id", index=True)
    amount_minor: int
    currency: str
    created_at: datetime = _utc()


class CartProposalRow(SQLModel, table=True):
    __tablename__ = "cart_proposal"

    id: int | None = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="user.id", index=True)
    items: list[dict[str, Any]] = _json(list)
    note: str
    status: str
    run_id: str
    created_at: datetime = _utc()
