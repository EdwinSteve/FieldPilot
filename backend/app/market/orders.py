"""Orders after checkout: the purchase record, cancellation and delivery (§4.15)."""

from collections.abc import Callable, Sequence

from app.domain.errors import NotFoundError
from app.domain.models import Money
from app.identity.models import Principal
from app.market.errors import ListingStateError
from app.market.listings import GRAMS_PER_KG, require_operator
from app.market.models import (
    CustomerOrder,
    ListingStatus,
    OrderStatus,
    Payout,
    StockMovement,
    StockReason,
)
from app.market.payments import PaymentGateway
from app.market.store import require_customer
from app.market.trace.ledger import append_trace
from app.market.trace.models import BizStep
from app.persistence.ports import UnitOfWork
from app.simulator.clock import Clock

UowFactory = Callable[[], UnitOfWork]


class OrderService:
    def __init__(self, uow: UowFactory, clock: Clock, payments: PaymentGateway) -> None:
        self._uow = uow
        self._clock = clock
        self._payments = payments

    def history(self, principal: Principal) -> Sequence[CustomerOrder]:
        """The customer's purchase record, newest first."""
        customer = require_customer(principal)
        with self._uow() as uow:
            return uow.orders.list(customer)

    def get(self, principal: Principal, order_id: int) -> CustomerOrder:
        customer = require_customer(principal)
        with self._uow() as uow:
            order = uow.orders.get(order_id)
        if order.customer_id != customer:
            raise NotFoundError("Order", order_id)  # another customer's order does not exist
        return order

    def cancel(self, principal: Principal, order_id: int) -> CustomerOrder:
        """While paid: refund, and every line gives its grams back to stock."""
        order = self.get(principal, order_id)
        now = self._clock.now()
        _require_paid(order)
        with self._uow() as uow:
            for line in order.lines:
                uow.listings.move_stock(
                    StockMovement(line.listing_id, line.quantity_kg * GRAMS_PER_KG,
                                  StockReason.RELEASE, f"order-{order_id}", now)
                )  # fmt: skip
            self._payments.refund(order.payment_ref, Money(order.total_minor, order.currency))
            cancelled = uow.orders.set_status(order_id, OrderStatus.CANCELLED, now)
            uow.commit()
        return cancelled

    def deliver(self, principal: Principal, order_id: int) -> CustomerOrder:
        """The operator hands it over: the sale enters each lot's chain, the farmer is paid."""
        require_operator(principal)
        now = self._clock.now()
        with self._uow() as uow:
            order = uow.orders.get(order_id)
            _require_paid(order)
            for line in order.lines:
                append_trace(uow, line.lot_code, BizStep.RETAIL_SELLING, now, principal.actor,
                             line.quantity_kg * GRAMS_PER_KG,
                             {"order_line": line.id})  # fmt: skip
                uow.orders.add_payout(
                    Payout(_stored(line.id), line.farmer_id,
                           line.price.farmer_minor * line.quantity_kg, line.price.currency, now)
                )  # fmt: skip
                if uow.listings.stock_g(line.listing_id) < GRAMS_PER_KG:
                    uow.listings.set_status(line.listing_id, ListingStatus.SOLD_OUT)
            delivered = uow.orders.set_status(order_id, OrderStatus.DELIVERED, now)
            uow.commit()
        return delivered

    def all_orders(self) -> Sequence[CustomerOrder]:
        """Every order, for the recommender's co-purchase and popularity scores."""
        with self._uow() as uow:
            return uow.orders.list()


def _require_paid(order: CustomerOrder) -> None:
    if order.status is not OrderStatus.PAID:
        raise ListingStateError(
            f"The order is {order.status}.", key="order_state", params={"status": order.status}
        )


def _stored(entity_id: int | None) -> int:
    if entity_id is None:
        raise ValueError("entity was not stored")
    return entity_id
