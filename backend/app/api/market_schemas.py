"""Request and response bodies of the market (D085, docs/api.md §8 and §9). Mapping only."""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.market.listings import GRAMS_PER_KG, ListingSummary
from app.market.models import (
    CartProposal,
    CustomerOrder,
    CustomerProfile,
    Discount,
    PriceBreakdown,
    Shipment,
    Warehouse,
)
from app.market.pricing import to_units
from app.market.recommend.scorers import Recommendation
from app.market.store import CartView, ProductView


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _kg(grams: int) -> float:
    return grams / GRAMS_PER_KG


class WarehouseOut(BaseModel):
    id: int
    code: str
    name: str
    municipality: str
    department: str
    cold_storage: bool

    @classmethod
    def of(cls, w: Warehouse) -> "WarehouseOut":
        return cls(
            id=w.id or 0,
            code=w.code,
            name=w.name,
            municipality=w.municipality,
            department=w.department,
            cold_storage=w.cold_storage,
        )


class NewListingIn(_In):
    farmer_price_per_kg_cop: Annotated[float, Field(gt=0, le=1_000_000)]
    quantity_kg: Annotated[int | None, Field(gt=0)] = None  # default: the whole harvest
    warehouse_id: int | None = None  # default: the Bogotá warehouse


class ShipmentOut(BaseModel):
    id: int
    listing_id: int
    warehouse_id: int
    status: str  # dispatched | received
    dispatched_kg: float
    received_kg: float | None
    temperature_c: float | None

    @classmethod
    def of(cls, s: Shipment) -> "ShipmentOut":
        return cls(
            id=s.id or 0,
            listing_id=s.listing_id,
            warehouse_id=s.warehouse_id,
            status="received" if s.received else "dispatched",
            dispatched_kg=_kg(s.dispatched_g),
            received_kg=None if s.received_g is None else _kg(s.received_g),
            temperature_c=s.temperature_c,
        )


class ListingOut(BaseModel):
    id: int
    lot_code: str
    crop: str
    crop_name: str
    status: str
    quantity_kg: float
    farmer_price_per_kg_cop: float
    shelf_price_per_kg_cop: float
    farmer_share_pct: float
    warehouse: WarehouseOut
    stock_kg: float
    sold_kg: float
    payouts_cop: float
    shipment: ShipmentOut | None
    best_before: date
    days_left: int
    clearance: "ClearanceOut | None"  # the automatic markdown in force today (D086)

    @classmethod
    def of(cls, s: ListingSummary, crop_name: str, price: PriceBreakdown) -> "ListingOut":
        listing = s.listing
        return cls(
            id=listing.id or 0,
            lot_code=listing.lot_code,
            crop=listing.crop,
            crop_name=crop_name,
            status=listing.status.value,
            quantity_kg=_kg(listing.quantity_g),
            farmer_price_per_kg_cop=to_units(listing.farmer_price_minor),
            shelf_price_per_kg_cop=to_units(price.total_minor),
            farmer_share_pct=price.farmer_share_pct,
            warehouse=WarehouseOut.of(s.warehouse),
            stock_kg=_kg(s.stock_g),
            sold_kg=_kg(s.sold_g),
            payouts_cop=to_units(s.payouts_minor),
            shipment=None if s.shipment is None else ShipmentOut.of(s.shipment),
            best_before=s.freshness.best_before,
            days_left=s.freshness.days_left,
            clearance=None if s.clearance is None else ClearanceOut.of(s.clearance),
        )


class ClearanceOut(BaseModel):
    discount_pct: int
    ends_on: date

    @classmethod
    def of(cls, d: Discount) -> "ClearanceOut":
        return cls(discount_pct=d.discount_pct, ends_on=d.ends_on)


class ReceiptIn(_In):
    received_kg: Annotated[float, Field(gt=0)]
    temperature_c: Annotated[float | None, Field(ge=-30, le=60)] = None


class NewOfferIn(_In):
    discount_pct: Annotated[int, Field(ge=1, le=99)]  # the service enforces the configured cap
    starts_on: date
    ends_on: date


class OfferOut(BaseModel):
    id: int
    listing_id: int
    discount_pct: int
    starts_on: date
    ends_on: date


class PriceOut(BaseModel):
    farmer_cop: float
    logistics_cop: float
    platform_cop: float
    total_cop: float
    farmer_share_pct: float
    discount_pct: int

    @classmethod
    def of(cls, p: PriceBreakdown) -> "PriceOut":
        return cls(
            farmer_cop=to_units(p.farmer_minor),
            logistics_cop=to_units(p.logistics_minor),
            platform_cop=to_units(p.platform_minor),
            total_cop=to_units(p.total_minor),
            farmer_share_pct=p.farmer_share_pct,
            discount_pct=p.discount_pct,
        )


class ProductOfferOut(BaseModel):
    source: str  # offer | clearance (D086)
    discount_pct: int
    ends_on: date

    @classmethod
    def of(cls, d: Discount) -> "ProductOfferOut":
        return cls(source=d.source.value, discount_pct=d.discount_pct, ends_on=d.ends_on)


class ProductOut(BaseModel):
    """Public: the producer's place, never a person's name or the plot's coordinates."""

    id: int
    crop: str
    crop_name: str
    unit: str = "kg"
    price: PriceOut
    offer: ProductOfferOut | None
    available_kg: float
    harvested_on: date
    best_before: date
    days_left: int
    producer: str
    warehouse: str
    lot_code: str
    passport_path: str

    @classmethod
    def of(cls, p: ProductView) -> "ProductOut":
        return cls(
            id=p.listing_id,
            crop=p.listing.crop,
            crop_name=p.crop_name,
            price=PriceOut.of(p.price),
            offer=None if p.offer is None else ProductOfferOut.of(p.offer),
            available_kg=float(p.available_g // GRAMS_PER_KG),
            harvested_on=p.harvested_on,
            best_before=p.best_before,
            days_left=p.days_left,
            producer=p.producer,
            warehouse=p.warehouse,
            lot_code=p.listing.lot_code,
            passport_path=f"/trace/{p.listing.lot_code}",
        )


class ProfileIn(_In):
    delivery_address: Annotated[str | None, Field(max_length=200)] = None
    consent_profiling: bool = False


class ProfileOut(BaseModel):
    delivery_address: str | None
    consent_profiling: bool
    consent_profiling_at: datetime | None

    @classmethod
    def of(cls, p: CustomerProfile) -> "ProfileOut":
        return cls(
            delivery_address=p.delivery_address,
            consent_profiling=p.consent_profiling_at is not None,
            consent_profiling_at=p.consent_profiling_at,
        )


class CartItemIn(_In):
    quantity_kg: Annotated[int, Field(ge=0, le=1000)]


class CartLineOut(BaseModel):
    listing_id: int
    crop_name: str
    quantity_kg: int
    unit_price_cop: float | None
    line_total_cop: float
    available_kg: float
    problem: str | None  # out_of_stock | not_available | expired


class CartOut(BaseModel):
    lines: list[CartLineOut]
    total_cop: float
    can_checkout: bool

    @classmethod
    def of(cls, cart: CartView) -> "CartOut":
        return cls(
            lines=[
                CartLineOut(
                    listing_id=line.listing_id,
                    crop_name=line.crop_name,
                    quantity_kg=line.quantity_kg,
                    unit_price_cop=None if line.price is None else to_units(line.price.total_minor),
                    line_total_cop=to_units(line.line_total_minor),
                    available_kg=float(line.available_g // GRAMS_PER_KG),
                    problem=line.problem,
                )
                for line in cart.lines
            ],
            total_cop=to_units(cart.total_minor),
            can_checkout=cart.can_checkout,
        )


class CheckoutIn(_In):
    delivery_address: Annotated[str | None, Field(max_length=200)] = None


class OrderLineOut(BaseModel):
    listing_id: int
    lot_code: str
    crop: str
    crop_name: str
    quantity_kg: int
    unit_price_cop: float
    line_total_cop: float
    passport_path: str


class OrderOut(BaseModel):
    id: int
    status: str
    total_cop: float
    payment_ref: str
    delivery_address: str
    placed_at: datetime
    delivered_at: datetime | None
    cancelled_at: datetime | None
    lines: list[OrderLineOut]

    @classmethod
    def of(cls, order: CustomerOrder, names: dict[str, str]) -> "OrderOut":
        return cls(
            id=order.id or 0,
            status=order.status.value,
            total_cop=to_units(order.total_minor),
            payment_ref=order.payment_ref,
            delivery_address=order.delivery_address,
            placed_at=order.placed_at,
            delivered_at=order.delivered_at,
            cancelled_at=order.cancelled_at,
            lines=[
                OrderLineOut(
                    listing_id=line.listing_id,
                    lot_code=line.lot_code,
                    crop=line.crop,
                    crop_name=names.get(line.crop, line.crop),
                    quantity_kg=line.quantity_kg,
                    unit_price_cop=to_units(line.price.total_minor),
                    line_total_cop=to_units(line.line_total_minor),
                    passport_path=f"/trace/{line.lot_code}",
                )
                for line in order.lines
            ],
        )


class RecommendationOut(BaseModel):
    product: ProductOut
    score: float
    reasons: list[str]
    evidence: dict[str, object]
    suggested_kg: int

    @classmethod
    def of(cls, r: Recommendation) -> "RecommendationOut":
        return cls(
            product=ProductOut.of(r.product),
            score=r.score,
            reasons=[code.value for code in r.reasons],
            evidence=dict(r.evidence),
            suggested_kg=r.suggested_kg,
        )


class AssistantIn(_In):
    question: Annotated[str, Field(min_length=1, max_length=1000)]


class ProposalOut(BaseModel):
    id: int
    items: list[dict[str, object]]
    note: str
    status: str

    @classmethod
    def of(cls, p: CartProposal) -> "ProposalOut":
        return cls(
            id=p.id or 0, items=[dict(i) for i in p.items], note=p.note, status=p.status.value
        )


class AssistantOut(BaseModel):
    run_id: str
    status: str
    answer: str | None
    proposal: ProposalOut | None
