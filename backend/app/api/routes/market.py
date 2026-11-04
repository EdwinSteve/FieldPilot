"""Selling the harvest: listings, the warehouse and offers (D085, docs/api.md §8)."""

from fastapi import APIRouter

from app.api.auth import PrincipalDep
from app.api.deps import ContainerDep
from app.api.market_schemas import (
    ListingOut,
    NewListingIn,
    NewOfferIn,
    OfferOut,
    ReceiptIn,
    ShipmentOut,
    WarehouseOut,
)
from app.container import Container
from app.market.listings import ListingSummary
from app.market.pricing import shelf_price

router = APIRouter(tags=["market"])


@router.get("/warehouses")
def warehouses(container: ContainerDep) -> list[WarehouseOut]:
    return [WarehouseOut.of(w) for w in container.listings.warehouses()]


@router.post("/lots/{code}/listings", status_code=201)
def create_listing(
    code: str, body: NewListingIn, principal: PrincipalDep, container: ContainerDep
) -> ListingOut:
    listing = container.listings.create(
        principal, code, body.farmer_price_per_kg_cop, body.quantity_kg, body.warehouse_id
    )
    return _listing_out(container, listing.id)


@router.get("/listings")
def my_listings(principal: PrincipalDep, container: ContainerDep) -> list[ListingOut]:
    return [_out(container, s) for s in container.listings.mine(principal)]


@router.post("/listings/{listing_id}/dispatch", status_code=201)
def dispatch(listing_id: int, principal: PrincipalDep, container: ContainerDep) -> ShipmentOut:
    """The farmer takes the listed harvest to the warehouse."""
    return ShipmentOut.of(container.listings.dispatch(principal, listing_id))


@router.post("/listings/{listing_id}/withdraw")
def withdraw(listing_id: int, principal: PrincipalDep, container: ContainerDep) -> ListingOut:
    listing = container.listings.withdraw(principal, listing_id)
    return _listing_out(container, listing.id)


@router.post("/listings/{listing_id}/offers", status_code=201)
def create_offer(
    listing_id: int, body: NewOfferIn, principal: PrincipalDep, container: ContainerDep
) -> OfferOut:
    offer = container.listings.add_offer(
        principal, listing_id, body.discount_pct, body.starts_on, body.ends_on
    )
    return OfferOut(id=offer.id or 0, listing_id=offer.listing_id, discount_pct=offer.discount_pct,
                    starts_on=offer.starts_on, ends_on=offer.ends_on)  # fmt: skip


@router.post("/listings/expire")
def expire(principal: PrincipalDep, container: ContainerDep) -> list[ListingOut]:
    """The operator writes off what passed its best-before day (D086)."""
    return [_listing_out(container, listing.id) for listing in container.listings.expire(principal)]


@router.post("/shipments/{shipment_id}/receive")
def receive(
    shipment_id: int, body: ReceiptIn, principal: PrincipalDep, container: ContainerDep
) -> ListingOut:
    """The warehouse operator weighs what arrived: only that becomes stock."""
    listing = container.listings.receive(
        principal, shipment_id, body.received_kg, body.temperature_c
    )
    return _listing_out(container, listing.id)


def _listing_out(container: Container, listing_id: int | None) -> ListingOut:
    if listing_id is None:
        raise ValueError("listing was not stored")
    return _out(container, container.listings.summary(listing_id))


def _out(container: Container, summary: ListingSummary) -> ListingOut:
    market = container.config.market
    listing = summary.listing
    price = shelf_price(listing.farmer_price_minor, market.fees, listing.currency)
    return ListingOut.of(summary, container.store.product_name(listing.crop), price)
