"""The store: catalogue and offers (public), and the customer's profile, cart, orders,
recommendations and shopping assistant (D085, docs/api.md §9)."""

from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.api.auth import PrincipalDep
from app.api.deps import ContainerDep
from app.api.errors import ChatUnavailableError
from app.api.market_schemas import (
    AssistantIn,
    AssistantOut,
    CartItemIn,
    CartOut,
    CartSuggestionOut,
    CheckoutIn,
    OrderOut,
    ProductOut,
    ProfileIn,
    ProfileOut,
    ProposalOut,
    RecommendationOut,
)
from app.container import Container
from app.market.models import CustomerOrder

router = APIRouter(tags=["store"])


@router.get("/store/products")
def products(
    container: ContainerDep, q: Annotated[str | None, Query(max_length=60)] = None
) -> list[ProductOut]:
    """Public: products in stock at the warehouse."""
    return [ProductOut.of(p) for p in container.store.catalogue(q)]


@router.get("/store/products/{listing_id}")
def product(listing_id: int, container: ContainerDep) -> ProductOut:
    return ProductOut.of(container.store.product(listing_id))


@router.get("/store/offers/today")
def offers_today(container: ContainerDep) -> list[ProductOut]:
    """Public: today's offers, validated on every read."""
    return [ProductOut.of(p) for p in container.store.offers_today()]


@router.get("/store/profile")
def profile(principal: PrincipalDep, container: ContainerDep) -> ProfileOut:
    return ProfileOut.of(container.store.profile(principal))


@router.put("/store/profile")
def save_profile(body: ProfileIn, principal: PrincipalDep, container: ContainerDep) -> ProfileOut:
    saved = container.store.save_profile(principal, body.delivery_address, body.consent_profiling)
    return ProfileOut.of(saved)


@router.get("/store/cart")
def cart(principal: PrincipalDep, container: ContainerDep) -> CartOut:
    return CartOut.of(container.store.cart(principal))


@router.put("/store/cart/items/{listing_id}")
def set_cart_item(
    listing_id: int, body: CartItemIn, principal: PrincipalDep, container: ContainerDep
) -> CartOut:
    """Whole kilograms; 0 removes the line."""
    return CartOut.of(container.store.set_item(principal, listing_id, body.quantity_kg))


@router.post("/store/checkout", status_code=201)
def checkout(
    principal: PrincipalDep, container: ContainerDep, body: CheckoutIn | None = None
) -> OrderOut:
    order = container.store.checkout(principal, None if body is None else body.delivery_address)
    return _order(container, order)


@router.get("/store/orders")
def orders(principal: PrincipalDep, container: ContainerDep) -> list[OrderOut]:
    """The customer's purchase record, newest first."""
    return [_order(container, o) for o in container.orders.history(principal)]


@router.get("/store/orders/{order_id}")
def order(order_id: int, principal: PrincipalDep, container: ContainerDep) -> OrderOut:
    return _order(container, container.orders.get(principal, order_id))


@router.post("/store/orders/{order_id}/cancel")
def cancel(order_id: int, principal: PrincipalDep, container: ContainerDep) -> OrderOut:
    return _order(container, container.orders.cancel(principal, order_id))


@router.post("/orders/{order_id}/deliver")
def deliver(order_id: int, principal: PrincipalDep, container: ContainerDep) -> OrderOut:
    """The warehouse operator hands the order over."""
    return _order(container, container.orders.deliver(principal, order_id))


@router.get("/store/recommendations")
def recommendations(
    principal: PrincipalDep, container: ContainerDep, k: Annotated[int, Query(ge=1, le=20)] = 5
) -> list[RecommendationOut]:
    return [RecommendationOut.of(r) for r in container.recommendations.for_customer(principal, k)]


@router.get("/store/cart/suggestion")
def cart_suggestion(
    principal: PrincipalDep,
    container: ContainerDep,
    prefer: Annotated[Literal["deal"] | None, Query()] = None,
    exclude: Annotated[str, Query(pattern=r"^\d+(,\d+)*$", max_length=500)] | None = None,
) -> CartSuggestionOut:
    """The assistant in the cart: one templated suggestion and its buttons (D087)."""
    shown = [int(i) for i in exclude.split(",")] if exclude else []
    suggestion = container.cart_suggestions.suggest(principal, prefer == "deal", shown)
    return CartSuggestionOut.of(suggestion)


@router.post("/store/assistant")
def assistant(body: AssistantIn, principal: PrincipalDep, container: ContainerDep) -> AssistantOut:
    """The shopping assistant proposes; the customer accepts. 503 under MOCK_LLM=1."""
    if container.shopper is None:
        raise ChatUnavailableError
    answer = container.shopper.ask(principal, body.question)
    return AssistantOut(
        run_id=answer.run_id,
        status=str(answer.status),
        answer=answer.answer,
        proposal=None if answer.proposal is None else ProposalOut.of(answer.proposal),
    )


@router.post("/store/cart-proposals/{proposal_id}/accept")
def accept_proposal(proposal_id: int, principal: PrincipalDep, container: ContainerDep) -> CartOut:
    return CartOut.of(container.store.accept_proposal(principal, proposal_id))


def _order(container: Container, order: CustomerOrder) -> OrderOut:
    names = {line.crop: container.store.product_name(line.crop) for line in order.lines}
    return OrderOut.of(order, names)
