"""Recommendations for one customer, from the catalogue and the orders (§4.16)."""

from collections.abc import Callable

from app.identity.models import Principal
from app.market.config import MarketConfig
from app.market.listings import COLOMBIA_UTC_OFFSET
from app.market.recommend.scorers import (
    DayOf,
    Recommendation,
    Weights,
    co_purchase,
    popularity,
    purchase_profile,
    recommend,
)
from app.market.store import StoreService, require_customer
from app.persistence.ports import UnitOfWork

UowFactory = Callable[[], UnitOfWork]
MAX_K = 20


class RecommendationService:
    def __init__(self, uow: UowFactory, store: StoreService, config: MarketConfig) -> None:
        self._uow = uow
        self._store = store
        self._weights = Weights(
            repurchase_due=config.weights["repurchase_due"],
            bought_together=config.weights["bought_together"],
            fresh_harvest=config.weights["fresh_harvest"],
            on_offer=config.weights["on_offer"],
            popular=config.weights["popular"],
            due_ratio=config.due_ratio,
            fresh_days=config.fresh_days,
            max_discount_pct=config.max_discount_pct,
        )
        self._day_of = DayOf(COLOMBIA_UTC_OFFSET)

    def for_customer(self, principal: Principal, k: int = 5) -> tuple[Recommendation, ...]:
        """Personal scores only with the customer's consent (Ley 1581 de 2012)."""
        customer = require_customer(principal)
        k = max(1, min(k, MAX_K))
        with self._uow() as uow:
            consent = uow.customers.profile(customer).consent_profiling_at is not None
            mine = uow.orders.list(customer) if consent else []
            every = uow.orders.list()
        today = self._store.today()
        profile = purchase_profile(mine, self._day_of) if consent else None
        return recommend(
            self._store.catalogue(),
            profile,
            co_purchase(every),
            popularity(every, self._day_of, today),
            today,
            self._weights,
            k,
        )
