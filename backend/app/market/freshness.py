"""How long a product stays sellable, and its markdown before then (D086): pure.

The product type is the crop, so its shelf life comes from
`shelf_life_days`. The markdown follows the share of that life left, so one
ladder fits a tomato (14 days) and a bean (180 days).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from app.market.config import ClearanceStep, MarketConfig
from app.market.models import Discount, DiscountSource, Listing
from app.market.pricing import deepest_allowed


@dataclass(frozen=True)
class Freshness:
    harvested_on: date
    shelf_days: int
    today: date

    @property
    def best_before(self) -> date:
        """The last day it is sold."""
        return self.harvested_on + timedelta(days=self.shelf_days)

    @property
    def days_left(self) -> int:
        return (self.best_before - self.today).days

    @property
    def expired(self) -> bool:
        return self.days_left < 0

    def reached(self, step: ClearanceStep) -> bool:
        """Integer form of days_left / shelf_days <= life_left_pct / 100."""
        return self.days_left * 100 <= step.life_left_pct * self.shelf_days

    def starts_on(self, step: ClearanceStep) -> date:
        """The first day `step` is reached."""
        return self.best_before - timedelta(days=step.life_left_pct * self.shelf_days // 100)


def clearance_step(
    fresh: Freshness, steps: Sequence[ClearanceStep]
) -> tuple[ClearanceStep, date] | None:
    """The deepest step reached, and the last day before the next one; None before any."""
    if fresh.expired:
        return None
    reached = [s for s in steps if fresh.reached(s)]
    if not reached:
        return None
    current = reached[-1]
    deeper = [s for s in steps[steps.index(current) + 1 :] if not fresh.reached(s)]
    ends_on = fresh.starts_on(deeper[0]) - timedelta(days=1) if deeper else fresh.best_before
    return current, ends_on


class ClearancePolicy:
    """The shelf life and the automatic markdown of a listing, as of a day."""

    def __init__(self, config: MarketConfig) -> None:
        self._config = config

    def freshness(self, crop: str, harvested_on: date, today: date) -> Freshness:
        return Freshness(harvested_on, self._config.shelf_life_days.get(crop, 0), today)

    def markdown(self, listing: Listing, fresh: Freshness) -> Discount | None:
        """Today's clearance discount, reduced if needed to keep the farmer's share."""
        found = clearance_step(fresh, self._config.clearance_steps)
        if found is None:
            return None
        step, ends_on = found
        pct = deepest_allowed(
            listing.farmer_price_minor, self._config.fees, listing.currency, step.discount_pct
        )
        return None if pct == 0 else Discount(DiscountSource.CLEARANCE, pct, ends_on)
