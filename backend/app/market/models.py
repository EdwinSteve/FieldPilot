"""Market value objects (architecture §4.15, D085). Grams and minor units: integers only."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum

from app.domain.models import JsonValue

MINOR_PER_UNIT = 100  # centavos per peso: Money keeps minor units (D080)


class ListingStatus(StrEnum):
    AWAITING_DELIVERY = "awaiting_delivery"  # listed, not yet at the warehouse
    IN_TRANSIT = "in_transit"  # the farmer dispatched it
    ACTIVE = "active"  # received: customers can buy it
    SOLD_OUT = "sold_out"
    WITHDRAWN = "withdrawn"  # by the farmer, before delivery
    EXPIRED = "expired"  # past its best-before day; the rest written off (D086)


class StockReason(StrEnum):
    RECEIPT = "receipt"
    SALE = "sale"
    RELEASE = "release"  # a cancelled order gives its grams back
    SHRINKAGE = "shrinkage"
    SPOILAGE = "spoilage"  # unsold at the best-before day (D086)


class OrderStatus(StrEnum):
    PAID = "paid"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class ProposalStatus(StrEnum):
    OPEN = "open"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"


@dataclass(frozen=True)
class Warehouse:
    code: str
    name: str
    municipality: str
    department: str
    cold_storage: bool
    id: int | None = None


@dataclass(frozen=True)
class Listing:
    lot_code: str
    farmer_id: int
    warehouse_id: int
    crop: str
    quantity_g: int
    farmer_price_minor: int  # per kg
    currency: str
    status: ListingStatus
    created_at: datetime
    id: int | None = None


@dataclass(frozen=True)
class Shipment:
    listing_id: int
    warehouse_id: int
    dispatched_g: int
    dispatched_at: datetime
    received_g: int | None = None
    temperature_c: float | None = None
    received_at: datetime | None = None
    received_by: str | None = None
    id: int | None = None

    @property
    def received(self) -> bool:
        return self.received_g is not None


@dataclass(frozen=True)
class StockMovement:
    listing_id: int
    delta_g: int
    reason: StockReason
    ref: str
    occurred_at: datetime
    id: int | None = None


@dataclass(frozen=True)
class Offer:
    listing_id: int
    discount_pct: int
    starts_on: date
    ends_on: date
    created_at: datetime
    id: int | None = None

    def valid_on(self, day: date) -> bool:
        return self.starts_on <= day <= self.ends_on


class DiscountSource(StrEnum):
    OFFER = "offer"  # the farmer's offer of the day
    CLEARANCE = "clearance"  # automatic, before the best-before day (D086)


@dataclass(frozen=True)
class Discount:
    """The discount a product sells at today, whatever gave it."""

    source: DiscountSource
    discount_pct: int
    ends_on: date  # the last day of this price


@dataclass(frozen=True)
class PriceBreakdown:
    """Per kg, in minor units: what the farmer, logistics and the platform get."""

    farmer_minor: int
    logistics_minor: int
    platform_minor: int
    discount_pct: int
    currency: str

    @property
    def total_minor(self) -> int:
        return self.farmer_minor + self.logistics_minor + self.platform_minor

    @property
    def farmer_share_pct(self) -> float:
        return round(100 * self.farmer_minor / self.total_minor, 1) if self.total_minor else 0.0


@dataclass(frozen=True)
class CustomerProfile:
    user_id: int
    delivery_address: str | None = None
    consent_profiling_at: datetime | None = None


@dataclass(frozen=True)
class CartItem:
    customer_id: int
    listing_id: int
    quantity_kg: int
    id: int | None = None


@dataclass(frozen=True)
class OrderLine:
    listing_id: int
    lot_code: str
    farmer_id: int
    crop: str
    quantity_kg: int
    price: PriceBreakdown  # per kg, frozen at checkout
    id: int | None = None
    order_id: int | None = None

    @property
    def line_total_minor(self) -> int:
        return self.price.total_minor * self.quantity_kg


@dataclass(frozen=True)
class CustomerOrder:
    customer_id: int
    status: OrderStatus
    total_minor: int
    currency: str
    payment_ref: str
    delivery_address: str
    placed_at: datetime
    lines: tuple[OrderLine, ...] = ()
    delivered_at: datetime | None = None
    cancelled_at: datetime | None = None
    id: int | None = None


@dataclass(frozen=True)
class Payout:
    order_line_id: int
    farmer_id: int
    amount_minor: int
    currency: str
    created_at: datetime
    id: int | None = None


@dataclass(frozen=True)
class CartProposal:
    customer_id: int
    items: tuple[Mapping[str, JsonValue], ...]  # {"listing_id", "quantity_kg"}
    note: str
    status: ProposalStatus
    created_at: datetime
    id: int | None = None
    run_id: str = ""
    meta: Mapping[str, JsonValue] = field(default_factory=dict)
