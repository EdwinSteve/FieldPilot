"""What a customer may need, from orders and the catalogue. Pure functions, no I/O.

Each score is in [0, 1] and comes with a reason code and its evidence, so
the assistant (and the screen) can say why a product is shown.
"""

import itertools
import math
import statistics
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import StrEnum

from app.domain.models import JsonValue
from app.market.models import CustomerOrder, OrderStatus
from app.market.store import ProductView

POPULAR_WINDOW_DAYS = 30
MIN_SCORE = 0.05  # below it a reason is noise, not a reason


class DayOf:
    """The local day an order was placed, in the warehouses' time zone."""

    def __init__(self, offset: timedelta) -> None:
        self._offset = offset

    def __call__(self, order: CustomerOrder) -> date:
        return (order.placed_at + self._offset).date()


class ReasonCode(StrEnum):
    REPURCHASE_DUE = "REPURCHASE_DUE"
    BOUGHT_TOGETHER = "BOUGHT_TOGETHER"
    FRESH_HARVEST = "FRESH_HARVEST"
    ON_OFFER = "ON_OFFER"
    POPULAR = "POPULAR"


@dataclass(frozen=True)
class Habit:
    crop: str
    orders: int
    last_bought: date
    median_interval_days: float | None  # None below two purchases
    usual_kg: int


@dataclass(frozen=True)
class PurchaseProfile:
    habits: Mapping[str, Habit]  # by crop
    recent_crops: frozenset[str]  # of the last order


@dataclass(frozen=True)
class Recommendation:
    product: ProductView
    score: float
    reasons: tuple[ReasonCode, ...]
    evidence: Mapping[str, JsonValue] = field(default_factory=dict)
    suggested_kg: int = 1


@dataclass(frozen=True)
class Weights:
    repurchase_due: float
    bought_together: float
    fresh_harvest: float
    on_offer: float
    popular: float
    due_ratio: float
    fresh_days: int
    max_discount_pct: int


def purchase_profile(orders: Sequence[CustomerOrder], day_of: DayOf) -> PurchaseProfile:
    """One customer's habits from their orders that were not cancelled."""
    kept = sorted((o for o in orders if o.status is not OrderStatus.CANCELLED),
                  key=lambda o: o.placed_at)  # fmt: skip
    days: dict[str, list[date]] = defaultdict(list)
    kilos: dict[str, list[int]] = defaultdict(list)
    for order in kept:
        for line in order.lines:
            days[line.crop].append(day_of(order))
            kilos[line.crop].append(line.quantity_kg)
    habits = {}
    for crop, bought in days.items():
        unique = sorted(set(bought))
        gaps = [(b - a).days for a, b in itertools.pairwise(unique)]
        habits[crop] = Habit(
            crop=crop,
            orders=len(unique),
            last_bought=unique[-1],
            median_interval_days=statistics.median(gaps) if gaps else None,
            usual_kg=max(1, round(statistics.median(kilos[crop]))),
        )
    recent = frozenset(line.crop for line in kept[-1].lines) if kept else frozenset()
    return PurchaseProfile(habits, recent)


def co_purchase(orders: Sequence[CustomerOrder]) -> Mapping[str, Mapping[str, float]]:
    """Item-item cosine over every order basket: how often two crops are bought together."""
    count: dict[str, int] = defaultdict(int)
    pairs: dict[tuple[str, str], int] = defaultdict(int)
    for order in orders:
        if order.status is OrderStatus.CANCELLED:
            continue
        basket = sorted({line.crop for line in order.lines})
        for crop in basket:
            count[crop] += 1
        for i, a in enumerate(basket):
            for b in basket[i + 1 :]:
                pairs[(a, b)] += 1
    similarity: dict[str, dict[str, float]] = defaultdict(dict)
    for (a, b), together in pairs.items():
        value = together / math.sqrt(count[a] * count[b])
        similarity[a][b] = similarity[b][a] = value
    return similarity


def popularity(orders: Sequence[CustomerOrder], day_of: DayOf, today: date) -> Mapping[str, int]:
    """Kilograms sold per crop in the last 30 days."""
    since = today - timedelta(days=POPULAR_WINDOW_DAYS)
    sold: dict[str, int] = defaultdict(int)
    for order in orders:
        if order.status is OrderStatus.CANCELLED or day_of(order) < since:
            continue
        for line in order.lines:
            sold[line.crop] += line.quantity_kg
    return sold


def recommend(
    products: Sequence[ProductView],
    profile: PurchaseProfile | None,  # None: no consent to personal scores (§7.4)
    similarity: Mapping[str, Mapping[str, float]],
    sold: Mapping[str, int],
    today: date,
    weights: Weights,
    k: int,
) -> tuple[Recommendation, ...]:
    """The k best products, each with the reasons that put it there."""
    top_sold = max(sold.values(), default=0)
    ranked = [
        _score(product, profile, similarity, sold, top_sold, today, weights) for product in products
    ]
    ranked.sort(key=lambda r: (-r.score, r.product.listing_id))
    return tuple(r for r in ranked if r.score > 0)[:k]


def _score(
    product: ProductView,
    profile: PurchaseProfile | None,
    similarity: Mapping[str, Mapping[str, float]],
    sold: Mapping[str, int],
    top_sold: int,
    today: date,
    weights: Weights,
) -> Recommendation:
    crop = product.listing.crop
    parts: list[tuple[ReasonCode, float, float, dict[str, JsonValue]]] = []
    habit = None if profile is None else profile.habits.get(crop)
    if habit is not None and habit.median_interval_days:
        since = (today - habit.last_bought).days
        ratio = since / habit.median_interval_days
        if ratio >= weights.due_ratio:
            parts.append((ReasonCode.REPURCHASE_DUE, weights.repurchase_due, min(ratio, 2) / 2,
                          {"last_bought": habit.last_bought.isoformat(),
                           "median_interval_days": habit.median_interval_days,
                           "days_since": since}))  # fmt: skip
    if profile is not None and profile.recent_crops and crop not in profile.recent_crops:
        together = max((similarity.get(crop, {}).get(c, 0.0) for c in profile.recent_crops),
                       default=0.0)  # fmt: skip
        parts.append((ReasonCode.BOUGHT_TOGETHER, weights.bought_together, together,
                      {"with": list[JsonValue](sorted(profile.recent_crops))}))  # fmt: skip
    age = (today - product.harvested_on).days
    if 0 <= age <= weights.fresh_days:
        parts.append((ReasonCode.FRESH_HARVEST, weights.fresh_harvest,
                      1 - age / (weights.fresh_days + 1),
                      {"harvested_on": product.harvested_on.isoformat()}))  # fmt: skip
    if product.offer is not None:
        parts.append((ReasonCode.ON_OFFER, weights.on_offer,
                      product.offer.discount_pct / weights.max_discount_pct,
                      {"discount_pct": product.offer.discount_pct,
                       "ends_on": product.offer.ends_on.isoformat()}))  # fmt: skip
    if top_sold:
        parts.append((ReasonCode.POPULAR, weights.popular, sold.get(crop, 0) / top_sold,
                      {"kg_sold_30_days": sold.get(crop, 0)}))  # fmt: skip
    kept = [p for p in parts if p[2] >= MIN_SCORE]
    evidence: dict[str, JsonValue] = {}
    for _, _, _, detail in kept:
        evidence.update(detail)
    return Recommendation(
        product=product,
        score=round(sum(weight * value for _, weight, value, _ in kept), 3),
        reasons=tuple(code for code, _, _, _ in kept),
        evidence=evidence,
        suggested_kg=1 if habit is None else habit.usual_kg,
    )
