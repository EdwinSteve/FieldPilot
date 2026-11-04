"""The market end to end (D085): list, deliver to Bogotá, buy, hand over, trace and pay."""

import json
from collections.abc import Iterator
from dataclasses import dataclass, replace
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.agent.llm.mock import MockLLMClient
from app.agent.messages import LLMResponse, ToolCall
from app.container import Container
from app.domain.models import Plot
from app.identity.models import Principal, Role
from app.main import create_app
from app.market.models import StockReason
from app.market.trace.models import Grade
from app.services.cycles import Harvest, NewCycle
from app.services.gate_context import local_day
from app.services.shopper import ShopperService, StoreShopperPort
from app.settings import Settings

PASSWORD = "cafe-con-panela"


@dataclass(frozen=True)
class Market:
    client: TestClient
    container: Container
    farmer: dict[str, str]
    operator: dict[str, str]
    customer: dict[str, str]
    other_customer: dict[str, str]
    lot_code: str


def _login(client: TestClient, phone: str) -> dict[str, str]:
    token = client.post("/auth/login", json={"phone": phone, "password": PASSWORD}).json()
    return {"Authorization": f"Bearer {token['access_token']}"}


def _register(client: TestClient, phone: str, role: str) -> dict[str, str]:
    policy = client.get("/auth/privacy-policy").json()["version"]
    body = {
        "phone": phone,
        "full_name": "Test",
        "password": PASSWORD,
        "role": role,
        "accept_privacy_policy": True,
        "privacy_policy_version": policy,
    }
    tokens = client.post("/auth/register", json=body).json()["tokens"]
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture
def market(tmp_path: Path) -> Iterator[Market]:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'market.db'}",
        mock_llm=True,
        auth_jwt_secret="k" * 48,
        planner_site_builder="off",
    )
    app = create_app(settings)
    container: Container = app.state.container
    with TestClient(app) as client:
        farmer = _register(client, "3001234567", "farmer")
        customer = _register(client, "3157654321", "customer")
        other = _register(client, "3168887766", "customer")
        container.auth.create_account("3201112233", "Operaria", Role.OPERATOR, PASSWORD)
        operator = _login(client, "3201112233")
        farmer_id = client.get("/auth/me", headers=farmer).json()["id"]
        yield Market(
            client,
            container,
            farmer,
            operator,
            customer,
            other,
            _harvested_lot(container, farmer_id),
        )


def _harvested_lot(container: Container, farmer_id: int) -> str:
    """A plot of the farmer, a tomato cycle sown 30 days ago and harvested today."""
    now = container.runtime.clock.now()
    with container.runtime.uow() as uow:
        plot = uow.plots.add(
            Plot(
                "Neiva",
                2.93,
                -75.28,
                2.0,
                now,
                utc_offset_hours=-5.0,
                municipality="Neiva",
                department="Huila",
            )
        )
        assert plot.id is not None
        uow.plot_members.add(plot.id, farmer_id)
        uow.commit()
    farmer = Principal(farmer_id, Role.FARMER)
    today = local_day(now, plot)
    cycle = container.cycles.start(
        farmer, plot.id, NewCycle("tomato", today - timedelta(days=30), accept_own_risk=True)
    )
    assert cycle.id is not None
    lot = container.cycles.harvest(farmer, cycle.id, Harvest(today, 100.0, Grade.FIRST))
    return lot.code


def _listed_and_received(m: Market, kg: float = 99.5) -> int:
    listing = m.client.post(
        f"/lots/{m.lot_code}/listings", json={"farmer_price_per_kg_cop": 3000}, headers=m.farmer
    ).json()
    shipment = m.client.post(f"/listings/{listing['id']}/dispatch", headers=m.farmer).json()
    received = m.client.post(
        f"/shipments/{shipment['id']}/receive",
        json={"received_kg": kg, "temperature_c": 9.0},
        headers=m.operator,
    )
    assert received.status_code == 200, received.json()
    listing_id: int = listing["id"]
    return listing_id


def _buy(m: Market, listing_id: int, kg: int, headers: dict[str, str] | None = None) -> Any:
    who = headers or m.customer
    m.client.put("/store/profile", json={"delivery_address": "Calle 80, Bogotá"}, headers=who)
    m.client.put(f"/store/cart/items/{listing_id}", json={"quantity_kg": kg}, headers=who)
    return m.client.post("/store/checkout", headers=who)


# --- the farmer lists, the warehouse receives ---------------------------------------------


def test_a_listing_shows_the_price_split_and_waits_for_the_warehouse(market: Market) -> None:
    response = market.client.post(
        f"/lots/{market.lot_code}/listings",
        json={"farmer_price_per_kg_cop": 3000},
        headers=market.farmer,
    )

    assert response.status_code == 201, response.json()
    listing = response.json()
    assert listing["status"] == "awaiting_delivery"
    assert (listing["farmer_price_per_kg_cop"], listing["shelf_price_per_kg_cop"]) == (3000, 3450)
    assert listing["farmer_share_pct"] == 87.0
    assert listing["warehouse"]["code"] == "BOG-01"  # the default warehouse in Bogotá
    assert listing["quantity_kg"] == 100.0
    assert market.client.get("/store/products").json() == []  # not sold before the receipt
    assert market.client.get(f"/store/products/{listing['id']}").status_code == 404


def test_a_lot_is_listed_once_and_never_below_the_farmers_share(market: Market) -> None:
    cheap = market.client.post(
        f"/lots/{market.lot_code}/listings",
        json={"farmer_price_per_kg_cop": 500},
        headers=market.farmer,
    )
    assert (cheap.status_code, cheap.json()["error"]) == (422, "PriceTooLowError")

    body = {"farmer_price_per_kg_cop": 3000}
    first = market.client.post(
        f"/lots/{market.lot_code}/listings", json=body, headers=market.farmer
    )
    assert first.status_code == 201
    again = market.client.post(
        f"/lots/{market.lot_code}/listings", json=body, headers=market.farmer
    )
    assert again.status_code == 409


def test_only_the_lots_farmer_lists_and_only_an_operator_receives(market: Market) -> None:
    body = {"farmer_price_per_kg_cop": 3000}
    stranger = market.client.post(
        f"/lots/{market.lot_code}/listings", json=body, headers=market.customer
    )
    assert stranger.status_code == 403
    listing = market.client.post(
        f"/lots/{market.lot_code}/listings", json=body, headers=market.farmer
    ).json()
    shipment = market.client.post(f"/listings/{listing['id']}/dispatch", headers=market.farmer)
    assert shipment.status_code == 201
    receipt = {"received_kg": 99.5}
    by_farmer = market.client.post(
        f"/shipments/{shipment.json()['id']}/receive", json=receipt, headers=market.farmer
    )
    assert by_farmer.status_code == 403
    too_much = market.client.post(
        f"/shipments/{shipment.json()['id']}/receive",
        json={"received_kg": 101},
        headers=market.operator,
    )
    assert too_much.status_code == 422


def test_what_the_warehouse_receives_becomes_the_public_catalogue(market: Market) -> None:
    listing_id = _listed_and_received(market)

    [product] = market.client.get("/store/products").json()  # public: no token
    assert product["id"] == listing_id
    assert product["available_kg"] == 99.0  # whole kilograms are sold
    assert product["producer"] == "Producer from Neiva, Huila"
    assert product["warehouse"] == "FieldPilot Bogotá D.C. warehouse"
    assert product["passport_path"] == f"/trace/{market.lot_code}"
    assert market.client.get("/store/products", params={"q": "potato"}).json() == []


# --- offers of the day --------------------------------------------------------------------


def test_an_offer_of_the_day_lowers_the_price_but_keeps_the_farmers_share(market: Market) -> None:
    listing_id = _listed_and_received(market)
    today = market.container.store.today()
    offer = {
        "discount_pct": 15,
        "starts_on": today.isoformat(),
        "ends_on": (today + timedelta(days=2)).isoformat(),
    }

    created = market.client.post(
        f"/listings/{listing_id}/offers", json=offer, headers=market.farmer
    )

    assert created.status_code == 201, created.json()
    [deal] = market.client.get("/store/offers/today").json()
    assert deal["price"]["discount_pct"] == 15
    assert deal["price"]["farmer_cop"] == 2550.0
    assert deal["price"]["farmer_share_pct"] >= 80
    too_deep = offer | {"discount_pct": 31}
    response = market.client.post(
        f"/listings/{listing_id}/offers", json=too_deep, headers=market.farmer
    )
    assert response.status_code == 422
    too_long = offer | {"ends_on": (today + timedelta(days=7)).isoformat()}
    response = market.client.post(
        f"/listings/{listing_id}/offers", json=too_long, headers=market.farmer
    )
    assert response.status_code == 422


def _days_later(m: Market, days: int) -> None:
    m.container.runtime.clock.advance(timedelta(days=days))


def test_a_tomato_near_its_best_before_day_is_marked_down_by_itself(market: Market) -> None:
    listing_id = _listed_and_received(market)
    _days_later(market, 12)  # a tomato keeps 14 days: 2 are left

    [deal] = market.client.get("/store/offers/today").json()
    [listing] = market.client.get("/listings", headers=market.farmer).json()

    assert deal["id"] == listing_id and deal["days_left"] == 2
    assert deal["offer"]["source"] == "clearance"
    assert (deal["price"]["discount_pct"], deal["price"]["farmer_cop"]) == (20, 2400.0)
    assert listing["clearance"]["discount_pct"] == 20 and listing["days_left"] == 2
    assert market.client.post("/listings/expire", headers=market.operator).json() == []


def test_the_deeper_of_the_farmers_offer_and_the_clearance_applies(market: Market) -> None:
    listing_id = _listed_and_received(market)
    _days_later(market, 12)
    today = market.container.store.today()
    offer = {"discount_pct": 25, "starts_on": today.isoformat(), "ends_on": today.isoformat()}
    market.client.post(f"/listings/{listing_id}/offers", json=offer, headers=market.farmer)

    [deal] = market.client.get("/store/offers/today").json()

    assert (deal["offer"]["source"], deal["price"]["discount_pct"]) == ("offer", 25)


def test_past_its_best_before_day_a_product_is_not_sold_and_is_written_off(
    market: Market,
) -> None:
    listing_id = _listed_and_received(market)
    who = market.customer
    market.client.put(f"/store/cart/items/{listing_id}", json={"quantity_kg": 2}, headers=who)
    _days_later(market, 15)

    assert market.client.get("/store/products").json() == []
    cart = market.client.get("/store/cart", headers=who).json()
    assert (cart["lines"][0]["problem"], cart["can_checkout"]) == ("expired", False)
    again = market.client.put(f"/store/cart/items/{listing_id}", json={"quantity_kg": 1},
                              headers=who)  # fmt: skip
    assert again.status_code == 404
    assert market.client.post("/listings/expire", headers=market.farmer).status_code == 403

    [expired] = market.client.post("/listings/expire", headers=market.operator).json()

    assert (expired["status"], expired["stock_kg"]) == ("expired", 0.0)
    with market.container.runtime.uow() as uow:
        assert uow.listings.moved_g(listing_id, StockReason.SPOILAGE) == 99_500
    assert market.client.post("/listings/expire", headers=market.operator).json() == []


# --- the customer buys --------------------------------------------------------------------


def test_the_store_needs_a_customer_account(market: Market) -> None:
    assert market.client.get("/store/cart").status_code == 401
    assert market.client.get("/store/cart", headers=market.farmer).status_code == 403


def test_the_cart_refuses_more_than_the_stock(market: Market) -> None:
    listing_id = _listed_and_received(market)
    response = market.client.put(
        f"/store/cart/items/{listing_id}", json={"quantity_kg": 120}, headers=market.customer
    )
    assert (response.status_code, response.json()["error"]) == (409, "OutOfStockError")


def test_checkout_pays_records_the_purchase_and_lowers_the_stock(market: Market) -> None:
    listing_id = _listed_and_received(market)
    empty = market.client.post("/store/checkout", headers=market.customer)
    assert empty.status_code == 409

    response = _buy(market, listing_id, 3)

    assert response.status_code == 201, response.json()
    order = response.json()
    assert order["status"] == "paid" and order["payment_ref"].startswith("MOCK-")
    assert order["total_cop"] == 3 * 3450.0
    [line] = order["lines"]
    assert (line["lot_code"], line["quantity_kg"]) == (market.lot_code, 3)
    assert market.client.get("/store/cart", headers=market.customer).json()["lines"] == []
    assert [
        o["id"] for o in market.client.get("/store/orders", headers=market.customer).json()
    ] == [order["id"]]
    [mine] = market.client.get("/listings", headers=market.farmer).json()
    assert (mine["stock_kg"], mine["sold_kg"]) == (96.5, 3.0)
    other = market.client.get(f"/store/orders/{order['id']}", headers=market.other_customer)
    assert other.status_code == 404  # another customer's order does not exist


def test_delivery_writes_the_sale_into_the_passport_and_pays_the_farmer(market: Market) -> None:
    listing_id = _listed_and_received(market)
    order = _buy(market, listing_id, 3).json()
    assert (
        market.client.post(f"/orders/{order['id']}/deliver", headers=market.customer).status_code
        == 403
    )

    delivered = market.client.post(f"/orders/{order['id']}/deliver", headers=market.operator)

    assert delivered.json()["status"] == "delivered"
    passport = market.client.get(f"/trace/{market.lot_code}").json()
    assert [s["step"] for s in passport["journey"]] == [
        "commissioning",
        "shipping",
        "receiving",
        "retail_selling",
    ]
    assert passport["journey"][2]["place"] == "FieldPilot Bogotá D.C. warehouse"
    assert passport["integrity"]["verified"] is True
    [mine] = market.client.get("/listings", headers=market.farmer).json()
    assert mine["payouts_cop"] == 3 * 3000.0
    cancel = market.client.post(f"/store/orders/{order['id']}/cancel", headers=market.customer)
    assert cancel.status_code == 409  # delivered is final


def test_a_cancelled_order_gives_its_stock_back(market: Market) -> None:
    listing_id = _listed_and_received(market)
    order = _buy(market, listing_id, 5).json()

    cancelled = market.client.post(f"/store/orders/{order['id']}/cancel", headers=market.customer)

    assert cancelled.json()["status"] == "cancelled"
    with market.container.runtime.uow() as uow:
        assert (
            uow.listings.moved_g(listing_id, StockReason.RELEASE) == 5000
        )  # a release, not a sale
    [mine] = market.client.get("/listings", headers=market.farmer).json()
    assert (mine["stock_kg"], mine["sold_kg"]) == (99.5, 0.0)


# --- recommendations and the assistant ----------------------------------------------------


def test_recommendations_explain_themselves_and_respect_consent(market: Market) -> None:
    listing_id = _listed_and_received(market)
    _buy(market, listing_id, 2, market.other_customer)

    [rec] = market.client.get("/store/recommendations", headers=market.customer).json()

    assert rec["product"]["id"] == listing_id
    assert "FRESH_HARVEST" in rec["reasons"] and "POPULAR" in rec["reasons"]
    assert "REPURCHASE_DUE" not in rec["reasons"]  # no consent to personal scores yet


def test_the_assistant_is_off_without_a_model(market: Market) -> None:
    response = market.client.post(
        "/store/assistant", json={"question": "What should I buy?"}, headers=market.customer
    )
    assert response.status_code == 503


def _assistant(market: Market, responses: list[LLMResponse]) -> None:
    """Swap in the assistant around a scripted model, as live mode wires it."""
    c = market.container

    def port_for(principal: Principal, run_id: str) -> StoreShopperPort:
        return StoreShopperPort(
            principal, c.store, c.orders, c.recommendations, c.passports, c.runtime.clock, run_id
        )

    shopper = ShopperService(
        MockLLMClient(responses), c.config.shopper, 6, port_for, lambda: "run-1", c.store.proposal
    )
    market.client.app.state.container = replace(c, shopper=shopper)  # type: ignore[attr-defined]


def _call(name: str, arguments: dict[str, Any]) -> LLMResponse:
    return LLMResponse(None, ToolCall(f"c-{name}", name, json.dumps(arguments)))


def test_the_assistant_proposes_a_cart_that_only_the_customer_accepts(market: Market) -> None:
    listing_id = _listed_and_received(market)
    _assistant(
        market,
        [
            _call("search_products", {"query": "tomato"}),
            _call(
                "propose_cart",
                {
                    "items": [{"listing_id": listing_id, "quantity_kg": 2}],
                    "note": "Two kilos for the sauce.",
                },
            ),
            _call("answer_customer", {"text": "Fresh tomato at $3,450 per kg; I proposed 2 kg."}),
        ],
    )

    response = market.client.post(
        "/store/assistant", json={"question": "Tomato sauce?"}, headers=market.customer
    )

    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["answer"].startswith("Fresh tomato")
    assert body["proposal"]["status"] == "open"
    assert market.client.get("/store/cart", headers=market.customer).json()["lines"] == []
    accepted = market.client.post(
        f"/store/cart-proposals/{body['proposal']['id']}/accept", headers=market.customer
    )
    assert [line["quantity_kg"] for line in accepted.json()["lines"]] == [2]
    stolen = market.client.post(
        f"/store/cart-proposals/{body['proposal']['id']}/accept", headers=market.other_customer
    )
    assert stolen.status_code == 404


def test_the_assistant_cannot_quote_a_price_no_tool_returned(market: Market) -> None:
    _listed_and_received(market)
    _assistant(
        market,
        [
            _call("search_products", {"query": "tomato"}),
            _call("answer_customer", {"text": "Tomato is $1,000 per kg today."}),
            _call("answer_customer", {"text": "Tomato is $3,450 per kg today."}),
        ],
    )

    body = market.client.post(
        "/store/assistant", json={"question": "Price?"}, headers=market.customer
    ).json()

    assert body["answer"] == "Tomato is $3,450 per kg today."  # the invented price was refused


def test_personal_recommendations_need_the_customers_consent(market: Market) -> None:
    listing_id = _listed_and_received(market)
    actor = "admin:test"
    for _ in range(2):  # a habit: every 7 days
        _buy(market, listing_id, 2)
        market.container.clock_service.advance(actor, timedelta(days=7))

    without = market.client.get("/store/recommendations", headers=market.customer).json()
    market.client.put(
        "/store/profile",
        json={"delivery_address": "Calle 80, Bogotá", "consent_profiling": True},
        headers=market.customer,
    )
    with_consent = market.client.get("/store/recommendations", headers=market.customer).json()

    assert all("REPURCHASE_DUE" not in r["reasons"] for r in without)
    assert "REPURCHASE_DUE" in with_consent[0]["reasons"]
