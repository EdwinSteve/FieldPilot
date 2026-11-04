"""The customer's side of the market: catalogue, offers, profile, cart, checkout (§4.15)."""

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

from app.autonomy.messages import MessageCatalog
from app.domain.errors import NotFoundError
from app.domain.models import Money
from app.identity.errors import ForbiddenError
from app.identity.models import Principal, Role
from app.market.config import MarketConfig
from app.market.errors import EmptyCartError, OutOfStockError, PaymentDeclinedError
from app.market.freshness import ClearancePolicy
from app.market.listings import COLOMBIA_UTC_OFFSET, GRAMS_PER_KG
from app.market.models import (
    CartProposal,
    CustomerOrder,
    CustomerProfile,
    Discount,
    DiscountSource,
    Listing,
    ListingStatus,
    Offer,
    OrderLine,
    OrderStatus,
    PriceBreakdown,
    ProposalStatus,
    StockMovement,
    StockReason,
)
from app.market.payments import PaymentGateway
from app.market.pricing import respects_share, shelf_price
from app.persistence.ports import UnitOfWork
from app.simulator.clock import Clock

UowFactory = Callable[[], UnitOfWork]
MAX_KG_PER_LINE = 1000


@dataclass(frozen=True)
class ProductView:
    """An active listing as a customer sees it: never the farmer's name or the plot."""

    listing: Listing
    crop_name: str
    price: PriceBreakdown  # per kg, with today's deepest discount
    offer: Discount | None  # the farmer's offer or the clearance markdown (D086)
    available_g: int
    harvested_on: date
    best_before: date
    days_left: int
    producer: str
    municipality: str
    department: str
    warehouse: str

    @property
    def listing_id(self) -> int:
        return _stored(self.listing.id)

    @property
    def expired(self) -> bool:
        return self.days_left < 0


@dataclass(frozen=True)
class CartLine:
    listing_id: int
    crop_name: str
    quantity_kg: int
    price: PriceBreakdown | None  # None when the listing is no longer sold
    available_g: int
    problem: str | None  # out_of_stock | not_available | expired

    @property
    def line_total_minor(self) -> int:
        return 0 if self.price is None else self.price.total_minor * self.quantity_kg


@dataclass(frozen=True)
class CartView:
    lines: tuple[CartLine, ...]
    currency: str

    @property
    def total_minor(self) -> int:
        return sum(line.line_total_minor for line in self.lines)

    @property
    def can_checkout(self) -> bool:
        return bool(self.lines) and all(line.problem is None for line in self.lines)


def require_customer(principal: Principal) -> int:
    """Store routes need a customer account, even in the demo (D085)."""
    if principal.user_id is None or principal.role not in {Role.CUSTOMER, Role.ADMIN}:
        raise ForbiddenError("Log in with a customer account to shop.", key="customer_account")
    return principal.user_id


class StoreService:
    def __init__(
        self,
        uow: UowFactory,
        clock: Clock,
        config: MarketConfig,
        messages: MessageCatalog,
        payments: PaymentGateway,
        clearance: ClearancePolicy,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._config = config
        self._messages = messages
        self._payments = payments
        self._clearance = clearance

    def today(self) -> date:
        return (self._clock.now() + COLOMBIA_UTC_OFFSET).date()

    def catalogue(self, query: str | None = None) -> Sequence[ProductView]:
        """Active listings with stock, before their best-before day; `query` matches the
        crop's id or name."""
        with self._uow() as uow:
            products = [
                self._product(uow, listing)
                for listing in uow.listings.list(status=ListingStatus.ACTIVE)
            ]
        wanted = (query or "").strip().lower()
        return [
            p
            for p in products
            if p.available_g >= GRAMS_PER_KG
            and not p.expired
            and (not wanted or wanted in p.listing.crop or wanted in p.crop_name.lower())
        ]

    def product(self, listing_id: int) -> ProductView:
        with self._uow() as uow:
            return self._sellable(uow, listing_id)

    def offers_today(self) -> Sequence[ProductView]:
        """Validated on read: today, an active listing with stock, the farmer's share kept;
        a clearance markdown counts as an offer (D086)."""
        return [p for p in self.catalogue() if p.offer is not None]

    def profile(self, principal: Principal) -> CustomerProfile:
        customer = require_customer(principal)
        with self._uow() as uow:
            return uow.customers.profile(customer)

    def save_profile(
        self, principal: Principal, address: str | None, consent_profiling: bool
    ) -> CustomerProfile:
        customer = require_customer(principal)
        with self._uow() as uow:
            current = uow.customers.profile(customer)
            consent = current.consent_profiling_at if consent_profiling else None
            if consent_profiling and consent is None:
                consent = self._clock.now()
            saved = uow.customers.save_profile(CustomerProfile(customer, address, consent))
            uow.commit()
        return saved

    def cart(self, principal: Principal) -> CartView:
        customer = require_customer(principal)
        with self._uow() as uow:
            return self._cart(uow, customer)

    def set_item(self, principal: Principal, listing_id: int, quantity_kg: int) -> CartView:
        """Whole kilograms; 0 removes the line. More than the stock is refused at once."""
        customer = require_customer(principal)
        if not 0 <= quantity_kg <= MAX_KG_PER_LINE:
            raise OutOfStockError(
                f"A line holds between 0 and {MAX_KG_PER_LINE} kg.",
                key="cart_quantity",
                params={"max_kg": MAX_KG_PER_LINE},
            )
        with self._uow() as uow:
            if quantity_kg > 0:
                self._check_stock(self._sellable(uow, listing_id), quantity_kg)
            uow.customers.set_cart_item(customer, listing_id, quantity_kg)
            uow.commit()
            return self._cart(uow, customer)

    def accept_proposal(self, principal: Principal, proposal_id: int) -> CartView:
        """The assistant proposed; the customer accepts: the lines go into the cart."""
        customer = require_customer(principal)
        with self._uow() as uow:
            proposal = uow.customers.proposal(proposal_id)
            if proposal.customer_id != customer:
                raise NotFoundError("CartProposal", proposal_id)
            for item in proposal.items:
                listing_id, kg = int(str(item["listing_id"])), int(str(item["quantity_kg"]))
                self._check_stock(self._sellable(uow, listing_id), kg)
                uow.customers.set_cart_item(customer, listing_id, kg)
            uow.customers.set_proposal_status(proposal_id, ProposalStatus.ACCEPTED)
            uow.commit()
            return self._cart(uow, customer)

    def proposal(self, proposal_id: int) -> CartProposal:
        with self._uow() as uow:
            return uow.customers.proposal(proposal_id)

    def add_proposal(self, proposal: CartProposal) -> CartProposal:
        with self._uow() as uow:
            stored = uow.customers.add_proposal(proposal)
            uow.commit()
        return stored

    def checkout(self, principal: Principal, address: str | None) -> CustomerOrder:
        """Reprice, check stock, charge, write the sale and the order, empty the cart."""
        customer = require_customer(principal)
        now = self._clock.now()
        with self._uow() as uow:
            cart = self._cart(uow, customer)
            if not cart.lines:
                raise EmptyCartError("The cart is empty.", key="empty_cart")
            if not cart.can_checkout:
                raise OutOfStockError(
                    "A product in the cart is no longer available in that quantity. "
                    "Review the cart.",
                    key="cart_changed",
                )
            delivery = (address or uow.customers.profile(customer).delivery_address or "").strip()
            if not delivery:
                raise EmptyCartError(
                    "A delivery address is needed.", key="delivery_address_missing"
                )
            amount = Money(cart.total_minor, cart.currency)
            payment = self._payments.charge(f"customer-{customer}", amount, uuid.uuid4().hex)
            if not payment.approved:
                raise PaymentDeclinedError("The payment was declined.", key="payment_declined")
            lines = []
            for line in cart.lines:
                listing = uow.listings.get(line.listing_id)
                uow.listings.move_stock(
                    StockMovement(line.listing_id, -line.quantity_kg * GRAMS_PER_KG,
                                  StockReason.SALE, payment.reference, now)
                )  # fmt: skip
                assert line.price is not None  # can_checkout guarantees it
                lines.append(
                    OrderLine(line.listing_id, listing.lot_code, listing.farmer_id,
                              listing.crop, line.quantity_kg, line.price)
                )  # fmt: skip
            order = uow.orders.add(
                CustomerOrder(customer, OrderStatus.PAID, cart.total_minor, cart.currency,
                              payment.reference, delivery, now, tuple(lines))
            )  # fmt: skip
            uow.customers.clear_cart(customer)
            uow.commit()
        return order

    def product_name(self, crop: str) -> str:
        return self._messages.crop_name(crop)

    def _cart(self, uow: UnitOfWork, customer: int) -> CartView:
        lines = []
        for item in uow.customers.cart(customer):
            listing = uow.listings.get(item.listing_id)
            name = self._messages.crop_name(listing.crop)
            if listing.status is not ListingStatus.ACTIVE:
                lines.append(CartLine(item.listing_id, name, item.quantity_kg, None, 0,
                                      "not_available"))  # fmt: skip
                continue
            product = self._product(uow, listing)
            if product.expired:
                lines.append(CartLine(item.listing_id, name, item.quantity_kg, None, 0,
                                      "expired"))  # fmt: skip
                continue
            short = product.available_g < item.quantity_kg * GRAMS_PER_KG
            lines.append(
                CartLine(item.listing_id, name, item.quantity_kg, product.price,
                         product.available_g, "out_of_stock" if short else None)
            )  # fmt: skip
        return CartView(tuple(lines), self._config.currency)

    def _product(self, uow: UnitOfWork, listing: Listing) -> ProductView:
        listing_id = _stored(listing.id)
        lot = uow.lots.get(listing.lot_code)
        plot = uow.plots.get(lot.plot_id)
        fresh = self._clearance.freshness(listing.crop, lot.harvested_on, self.today())
        offer = self._deepest(self._best_offer(uow.listings.offers(listing_id), listing),
                              self._clearance.markdown(listing, fresh))  # fmt: skip
        discount = 0 if offer is None else offer.discount_pct
        place = ", ".join(p for p in (plot.municipality, plot.department) if p)
        producer = (
            self._messages.label("producer_of", place=place)
            if place
            else self._messages.label("producer_unknown")
        )
        return ProductView(
            listing=listing,
            crop_name=self._messages.crop_name(listing.crop),
            price=shelf_price(
                listing.farmer_price_minor, self._config.fees, listing.currency, discount
            ),
            offer=offer,
            available_g=uow.listings.stock_g(listing_id),
            harvested_on=lot.harvested_on,
            best_before=fresh.best_before,
            days_left=fresh.days_left,
            producer=producer,
            municipality=plot.municipality,
            department=plot.department,
            warehouse=uow.warehouses.get(listing.warehouse_id).name,
        )

    @staticmethod
    def _deepest(*discounts: Discount | None) -> Discount | None:
        """One discount, never stacked: the deepest; the farmer's offer on a tie."""
        given = [d for d in discounts if d is not None]
        return max(given, key=lambda d: d.discount_pct, default=None)

    def _best_offer(self, offers: Sequence[Offer], listing: Listing) -> Discount | None:
        """Today's valid offers that still keep the farmer's share; the deepest wins."""
        today = self.today()
        valid = [
            o
            for o in offers
            if o.valid_on(today)
            and respects_share(
                shelf_price(listing.farmer_price_minor, self._config.fees, listing.currency,
                            o.discount_pct),
                self._config.fees,
            )
        ]  # fmt: skip
        best = max(valid, key=lambda o: o.discount_pct, default=None)
        return None if best is None else Discount(DiscountSource.OFFER, best.discount_pct,
                                                  best.ends_on)  # fmt: skip

    def _sellable(self, uow: UnitOfWork, listing_id: int) -> ProductView:
        """An active listing before its best-before day, or 404."""
        listing = uow.listings.get(listing_id)
        if listing.status is not ListingStatus.ACTIVE:
            raise NotFoundError("Product", listing_id)
        product = self._product(uow, listing)
        if product.expired:
            raise NotFoundError("Product", listing_id)
        return product

    @staticmethod
    def _check_stock(product: ProductView, quantity_kg: int) -> None:
        if product.available_g < quantity_kg * GRAMS_PER_KG:
            raise OutOfStockError(
                f"Only {product.available_g // GRAMS_PER_KG} kg of {product.crop_name} are left.",
                key="out_of_stock",
                params={"available_kg": product.available_g // GRAMS_PER_KG,
                        "crop": product.crop_name},
            )  # fmt: skip


def _stored(entity_id: int | None) -> int:
    if entity_id is None:
        raise ValueError("entity was not stored")
    return entity_id
