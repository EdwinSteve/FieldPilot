"""The farmer's side of the market: list a lot, take it to the warehouse, offer it (§4.15).

The operator's side, receiving at the warehouse, lives here too: it is the
step that turns a listing into stock.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from app.domain.errors import NotFoundError
from app.identity.access import AccessPolicy
from app.identity.errors import ForbiddenError
from app.identity.models import Principal, Role
from app.market.config import MarketConfig
from app.market.errors import (
    InvalidOfferError,
    InvalidReceiptError,
    ListingStateError,
    PriceTooLowError,
)
from app.market.freshness import ClearancePolicy, Freshness
from app.market.models import (
    MINOR_PER_UNIT,
    Discount,
    Listing,
    ListingStatus,
    Offer,
    Shipment,
    StockMovement,
    StockReason,
    Warehouse,
)
from app.market.pricing import respects_share, shelf_price
from app.market.trace.ledger import append_trace
from app.market.trace.models import BizStep
from app.persistence.ports import UnitOfWork
from app.simulator.clock import Clock

UowFactory = Callable[[], UnitOfWork]
GRAMS_PER_KG = 1000
COLOMBIA_UTC_OFFSET = timedelta(hours=-5)  # the warehouses' local day


@dataclass(frozen=True)
class ListingSummary:
    """A listing as its farmer sees it: where it is, what is left, what it earned."""

    listing: Listing
    warehouse: Warehouse
    stock_g: int
    sold_g: int
    payouts_minor: int
    shipment: Shipment | None
    freshness: Freshness
    clearance: Discount | None  # the automatic markdown in force today (D086)


def require_operator(principal: Principal) -> None:
    if principal.role not in {Role.OPERATOR, Role.ADMIN}:
        raise ForbiddenError("Only a warehouse operator can do this.", key="operator_only")


class ListingService:
    def __init__(
        self,
        uow: UowFactory,
        clock: Clock,
        config: MarketConfig,
        access: AccessPolicy,
        clearance: ClearancePolicy,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._config = config
        self._access = access
        self._clearance = clearance

    def today(self) -> date:
        return (self._clock.now() + COLOMBIA_UTC_OFFSET).date()

    def ensure_warehouses(self) -> None:
        """The configured warehouses exist; startup calls this (D085)."""
        with self._uow() as uow:
            for spec in self._config.warehouses:
                if uow.warehouses.find_by_code(spec.code) is None:
                    uow.warehouses.add(
                        Warehouse(spec.code, spec.name, spec.municipality, spec.department,
                                  spec.cold_storage)
                    )  # fmt: skip
            uow.commit()

    def warehouses(self) -> Sequence[Warehouse]:
        with self._uow() as uow:
            return uow.warehouses.list()

    def create(
        self,
        principal: Principal,
        lot_code: str,
        price_per_kg: float,
        quantity_kg: int | None,
        warehouse_id: int | None,
    ) -> Listing:
        """A member of the lot's plot lists it; one listing per lot (§4.15 rule 1)."""
        farmer_id = _farmer_id(principal)
        with self._uow() as uow:
            lot = uow.lots.get(lot_code)
        self._access.require_farm(principal, lot.plot_id)
        if lot.crop not in self._config.shelf_life_days:
            raise ListingStateError(
                f"{lot.crop} is not sold as food on this platform.",
                key="crop_not_sellable",
                params={"crop": lot.crop},
            )
        quantity_g = lot.quantity_g if quantity_kg is None else quantity_kg * GRAMS_PER_KG
        quantity_g -= quantity_g % GRAMS_PER_KG  # whole kilograms only
        if not 0 < quantity_g <= lot.quantity_g:
            raise ListingStateError(
                "The quantity must be whole kilograms, above 0 and at most the harvest.",
                key="listing_quantity",
            )
        price_minor = round(price_per_kg * MINOR_PER_UNIT)
        self._check_price(price_minor)
        with self._uow() as uow:
            if uow.listings.find_by_lot(lot_code) is not None:
                raise ListingStateError("This lot is already listed.", key="lot_already_listed")
            warehouse = self._warehouse(uow, warehouse_id)
            listing = uow.listings.add(
                Listing(
                    lot_code=lot_code,
                    farmer_id=farmer_id,
                    warehouse_id=_stored(warehouse.id),
                    crop=lot.crop,
                    quantity_g=quantity_g,
                    farmer_price_minor=price_minor,
                    currency=self._config.currency,
                    status=ListingStatus.AWAITING_DELIVERY,
                    created_at=self._clock.now(),
                )
            )
            uow.commit()
        return listing

    def dispatch(self, principal: Principal, listing_id: int) -> Shipment:
        """The farmer takes the listed kilograms to the warehouse (§4.15 rule 3)."""
        now = self._clock.now()
        with self._uow() as uow:
            listing = self._own(uow, principal, listing_id)
            _require_status(listing, ListingStatus.AWAITING_DELIVERY)
            warehouse = uow.warehouses.get(listing.warehouse_id)
            shipment = uow.listings.add_shipment(
                Shipment(listing_id, listing.warehouse_id, listing.quantity_g, now)
            )
            uow.listings.set_status(listing_id, ListingStatus.IN_TRANSIT)
            place = {"warehouse": warehouse.code, "warehouse_name": warehouse.name}
            append_trace(
                uow, listing.lot_code, BizStep.SHIPPING, now, principal.actor,
                listing.quantity_g, place,
            )  # fmt: skip
            uow.commit()
        return shipment

    def withdraw(self, principal: Principal, listing_id: int) -> Listing:
        with self._uow() as uow:
            listing = self._own(uow, principal, listing_id)
            _require_status(listing, ListingStatus.AWAITING_DELIVERY)
            withdrawn = uow.listings.set_status(listing_id, ListingStatus.WITHDRAWN)
            uow.commit()
        return withdrawn

    def receive(
        self,
        principal: Principal,
        shipment_id: int,
        received_kg: float,
        temperature_c: float | None,
    ) -> Listing:
        """The operator weighs what arrived; only that becomes stock."""
        require_operator(principal)
        now = self._clock.now()
        received_g = round(received_kg * GRAMS_PER_KG)
        with self._uow() as uow:
            shipment = uow.listings.get_shipment(shipment_id)
            listing = uow.listings.get(shipment.listing_id)
            if shipment.received or listing.status is not ListingStatus.IN_TRANSIT:
                raise ListingStateError(
                    "This shipment was already received.", key="shipment_received"
                )
            if not 0 < received_g <= shipment.dispatched_g:
                raise InvalidReceiptError(
                    "The kilograms received must be above 0 and at most those dispatched.",
                    key="invalid_receipt",
                )
            warehouse = uow.warehouses.get(shipment.warehouse_id)
            uow.listings.record_receipt(
                Shipment(shipment.listing_id, shipment.warehouse_id, shipment.dispatched_g,
                         shipment.dispatched_at, received_g, temperature_c, now,
                         principal.actor, shipment.id)
            )  # fmt: skip
            uow.listings.move_stock(
                StockMovement(_stored(listing.id), received_g, StockReason.RECEIPT,
                              f"shipment-{shipment_id}", now)
            )  # fmt: skip
            append_trace(uow, listing.lot_code, BizStep.RECEIVING, now, principal.actor,
                         received_g,
                         {"warehouse": warehouse.code, "warehouse_name": warehouse.name,
                          "temperature_c": temperature_c,
                          "shrinkage_g": shipment.dispatched_g - received_g})  # fmt: skip
            active = uow.listings.set_status(_stored(listing.id), ListingStatus.ACTIVE)
            uow.commit()
        return active

    def add_offer(
        self, principal: Principal, listing_id: int, discount_pct: int, starts: date, ends: date
    ) -> Offer:
        """A discount on the farmer's own active listing (§4.15 rule 5)."""
        if not 1 <= discount_pct <= self._config.max_discount_pct:
            raise InvalidOfferError(
                f"The discount must be between 1 and {self._config.max_discount_pct} %.",
                key="offer_discount",
                params={"max_pct": self._config.max_discount_pct},
            )
        if (
            not self.today() <= starts <= ends
            or (ends - starts).days >= self._config.max_offer_days
        ):
            raise InvalidOfferError(
                f"An offer starts today or later and lasts at most "
                f"{self._config.max_offer_days} days.",
                key="offer_dates",
                params={"max_days": self._config.max_offer_days},
            )
        with self._uow() as uow:
            listing = self._own(uow, principal, listing_id)
            _require_status(listing, ListingStatus.ACTIVE)
            self._check_price(listing.farmer_price_minor, discount_pct)
            offer = uow.listings.add_offer(
                Offer(listing_id, discount_pct, starts, ends, self._clock.now())
            )
            uow.commit()
        return offer

    def mine(self, principal: Principal) -> Sequence[ListingSummary]:
        """The farmer's listings; an admin sees all."""
        farmer = None if principal.role is Role.ADMIN else _farmer_id(principal)
        with self._uow() as uow:
            return [self._summarise(uow, listing)
                    for listing in uow.listings.list(farmer_id=farmer)]  # fmt: skip

    def summary(self, listing_id: int) -> ListingSummary:
        """One listing's state, for the response of a call that was already authorised."""
        with self._uow() as uow:
            return self._summarise(uow, uow.listings.get(listing_id))

    def expire_due(self) -> Sequence[Listing]:
        """Write off what is left of every active listing past its best-before day (D086).

        Bookkeeping only: the store already refuses an expired product.
        """
        now = self._clock.now()
        expired = []
        with self._uow() as uow:
            for listing in uow.listings.list(status=ListingStatus.ACTIVE):
                listing_id = _stored(listing.id)
                if not self._freshness(uow, listing).expired:
                    continue
                left = uow.listings.stock_g(listing_id)
                if left > 0:
                    uow.listings.move_stock(
                        StockMovement(listing_id, -left, StockReason.SPOILAGE, "best-before", now)
                    )
                expired.append(uow.listings.set_status(listing_id, ListingStatus.EXPIRED))
            uow.commit()
        return expired

    def expire(self, principal: Principal) -> Sequence[Listing]:
        require_operator(principal)
        return self.expire_due()

    def _check_price(self, farmer_price_minor: int, discount_pct: int = 0) -> None:
        fees = self._config.fees
        price = shelf_price(farmer_price_minor, fees, self._config.currency, discount_pct)
        if not respects_share(price, fees):
            raise PriceTooLowError(
                f"The farmer would keep {price.farmer_share_pct} % of the shelf price, under "
                f"the minimum of {fees.min_farmer_share_pct:g} %. Raise the price.",
                key="price_too_low",
                params={
                    "share_pct": price.farmer_share_pct,
                    "min_pct": fees.min_farmer_share_pct,
                },
            )

    def _warehouse(self, uow: UnitOfWork, warehouse_id: int | None) -> Warehouse:
        if warehouse_id is not None:
            return uow.warehouses.get(warehouse_id)
        default = uow.warehouses.find_by_code(self._config.warehouses[0].code)
        if default is None:
            raise NotFoundError("Warehouse", self._config.warehouses[0].code)
        return default

    def _freshness(self, uow: UnitOfWork, listing: Listing) -> Freshness:
        harvested_on = uow.lots.get(listing.lot_code).harvested_on
        return self._clearance.freshness(listing.crop, harvested_on, self.today())

    def _summarise(self, uow: UnitOfWork, listing: Listing) -> ListingSummary:
        listing_id = _stored(listing.id)
        sold = uow.listings.moved_g(listing_id, StockReason.SALE)
        released = uow.listings.moved_g(listing_id, StockReason.RELEASE)
        fresh = self._freshness(uow, listing)
        on_sale = listing.status is ListingStatus.ACTIVE
        return ListingSummary(
            listing,
            uow.warehouses.get(listing.warehouse_id),
            uow.listings.stock_g(listing_id),
            sold - released,
            uow.orders.payouts_minor(listing_id),
            uow.listings.shipment_for(listing_id),
            fresh,
            self._clearance.markdown(listing, fresh) if on_sale else None,
        )

    @staticmethod
    def _own(uow: UnitOfWork, principal: Principal, listing_id: int) -> Listing:
        listing = uow.listings.get(listing_id)
        if principal.role is not Role.ADMIN and listing.farmer_id != principal.user_id:
            raise ForbiddenError("This listing is not yours.", key="listing_not_yours")
        return listing


def _farmer_id(principal: Principal) -> int:
    """Selling needs a real farmer account, even in the demo (D085)."""
    if principal.user_id is None or principal.role not in {Role.FARMER, Role.ADMIN}:
        raise ForbiddenError("Log in with a farmer account to sell.", key="farmer_account")
    return principal.user_id


def _require_status(listing: Listing, status: ListingStatus) -> None:
    if listing.status is not status:
        raise ListingStateError(
            f"The listing is {listing.status}, not {status}.",
            key="listing_state",
            params={"status": listing.status.value},
        )


def _stored(entity_id: int | None) -> int:
    if entity_id is None:
        raise ValueError("entity was not stored")
    return entity_id
