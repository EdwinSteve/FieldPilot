"""The shelf price (D080) and the deterministic recommender (market.md §7.1). Pure."""

from datetime import UTC, date, datetime, timedelta

from app.market.config import MarketFees
from app.market.models import (
    CustomerOrder,
    Listing,
    ListingStatus,
    OrderLine,
    OrderStatus,
    PriceBreakdown,
)
from app.market.pricing import respects_share, shelf_price
from app.market.recommend.scorers import (
    DayOf,
    ReasonCode,
    Weights,
    co_purchase,
    purchase_profile,
    recommend,
)
from app.market.store import ProductView

FEES = MarketFees(logistics_per_kg=300, platform_pct=5, min_farmer_share_pct=80)
WEIGHTS = Weights(1.0, 0.6, 0.5, 0.7, 0.3, due_ratio=0.8, fresh_days=7, max_discount_pct=30)
DAY_OF = DayOf(timedelta(hours=-5))
TODAY = date(2026, 11, 20)


def test_the_shelf_price_adds_logistics_and_the_platform_share() -> None:
    price = shelf_price(300_000, FEES, "COP")  # COP 3,000 per kg, in centavos
    assert (price.farmer_minor, price.logistics_minor, price.platform_minor) == (
        300_000,
        30_000,
        15_000,
    )
    assert price.total_minor == 345_000 and price.farmer_share_pct == 87.0
    assert respects_share(price, FEES)


def test_a_discount_comes_off_the_farmers_price_and_may_break_the_share() -> None:
    assert shelf_price(300_000, FEES, "COP", 15).farmer_minor == 255_000
    cheap = shelf_price(100_000, FEES, "COP")  # COP 1,000: logistics weighs too much
    assert not respects_share(cheap, FEES)


def _order(day: date, *crops: str) -> CustomerOrder:
    price = PriceBreakdown(100_000, 30_000, 5_000, 0, "COP")
    placed = datetime(day.year, day.month, day.day, 17, tzinfo=UTC)
    lines = tuple(OrderLine(1, "FP-1", 7, crop, 2, price) for crop in crops)
    return CustomerOrder(9, OrderStatus.PAID, 0, "COP", "MOCK", "x", placed, lines)


def _product(listing_id: int, crop: str, harvested: date) -> ProductView:
    listing = Listing("FP-1", 7, 1, crop, 100_000, 300_000, "COP", ListingStatus.ACTIVE,
                      datetime(2026, 11, 1, tzinfo=UTC), listing_id)  # fmt: skip
    return ProductView(listing, crop.title(), shelf_price(300_000, FEES, "COP"), None, 100_000,
                       harvested, harvested + timedelta(days=14), "Producer from Neiva",
                       "Neiva", "Huila", "BOG")  # fmt: skip


def test_a_regular_purchase_becomes_due_after_its_usual_interval() -> None:
    orders = [_order(TODAY - timedelta(days=d), "tomato") for d in (21, 14, 7)]
    profile = purchase_profile(orders, DAY_OF)

    [rec] = recommend([_product(1, "tomato", TODAY - timedelta(days=30))], profile, {}, {},
                      TODAY, WEIGHTS, 5)  # fmt: skip

    assert rec.reasons == (ReasonCode.REPURCHASE_DUE,)
    assert rec.evidence["median_interval_days"] == 7
    assert rec.suggested_kg == 2


def test_crops_bought_together_are_suggested_together() -> None:
    every = [_order(TODAY - timedelta(days=d), "potato", "maize") for d in (9, 5)]
    profile = purchase_profile([_order(TODAY - timedelta(days=1), "potato")], DAY_OF)

    ranked = recommend([_product(1, "maize", TODAY - timedelta(days=30))], profile,
                       co_purchase(every), {}, TODAY, WEIGHTS, 5)  # fmt: skip

    assert ranked[0].reasons == (ReasonCode.BOUGHT_TOGETHER,)


def test_without_consent_only_shared_signals_rank() -> None:
    fresh = _product(1, "tomato", TODAY - timedelta(days=1))
    [rec] = recommend([fresh], None, {}, {"tomato": 10}, TODAY, WEIGHTS, 5)
    assert set(rec.reasons) == {ReasonCode.FRESH_HARVEST, ReasonCode.POPULAR}


def test_a_cancelled_order_is_not_a_habit() -> None:
    cancelled = _order(TODAY - timedelta(days=3), "tomato")
    cancelled = CustomerOrder(**{**cancelled.__dict__, "status": OrderStatus.CANCELLED})
    assert purchase_profile([cancelled], DAY_OF).habits == {}


def test_a_purchase_is_not_due_before_its_usual_interval() -> None:
    orders = [_order(TODAY - timedelta(days=d), "tomato") for d in (8, 1)]  # every 7 days
    profile = purchase_profile(orders, DAY_OF)

    ranked = recommend([_product(1, "tomato", TODAY - timedelta(days=30))], profile, {}, {},
                       TODAY, WEIGHTS, 5)  # fmt: skip

    assert ranked == ()  # bought yesterday: nothing is due, and nothing else applies
