"""Shelf life and the clearance ladder (D086). Pure."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from app.domain.errors import ConfigError
from app.market.config import MarketConfig, MarketFees, load_market_config
from app.market.freshness import ClearancePolicy, Freshness
from app.market.models import DiscountSource, Listing, ListingStatus
from app.market.pricing import deepest_allowed, respects_share, shelf_price

CONFIG_FILE = Path(__file__).parents[4] / "config" / "market.yaml"
FEES = MarketFees(logistics_per_kg=300, platform_pct=5, min_farmer_share_pct=80)
HARVEST = date(2026, 11, 1)


def _policy() -> ClearancePolicy:
    return ClearancePolicy(load_market_config(CONFIG_FILE))


def _listing(crop: str = "tomato", price_minor: int = 300_000) -> Listing:
    return Listing("FP-1", 7, 1, crop, 100_000, price_minor, "COP", ListingStatus.ACTIVE,
                   datetime(2026, 11, 1, tzinfo=UTC), 1)  # fmt: skip


def _markdown_with_days_left(crop: str, days_left: int, price_minor: int = 300_000) -> int:
    policy = _policy()
    probe = policy.freshness(crop, HARVEST, HARVEST)
    fresh = replace(probe, today=probe.best_before - timedelta(days=days_left))
    found = policy.markdown(_listing(crop, price_minor), fresh)
    return 0 if found is None else found.discount_pct


def test_the_best_before_day_comes_from_the_crops_shelf_life() -> None:
    fresh = _policy().freshness("tomato", HARVEST, HARVEST + timedelta(days=4))
    assert fresh.best_before == date(2026, 11, 15)
    assert (fresh.days_left, fresh.expired) == (10, False)


@pytest.mark.parametrize(
    ("days_left", "discount"),
    [(14, 0), (6, 0), (5, 10), (3, 10), (2, 20), (1, 35), (0, 35), (-1, 0)],
)
def test_a_tomato_is_marked_down_in_steps_as_its_life_runs_out(
    days_left: int, discount: int
) -> None:
    assert _markdown_with_days_left("tomato", days_left) == discount


def test_the_ladder_follows_the_share_of_life_left_not_days() -> None:
    assert _markdown_with_days_left("common_bean", 73) == 0
    assert _markdown_with_days_left("common_bean", 72) == 10
    assert _markdown_with_days_left("common_bean", 36) == 20
    assert _markdown_with_days_left("common_bean", 18) == 35


def test_a_markdown_ends_the_day_before_the_next_step_or_on_the_best_before_day() -> None:
    policy = _policy()
    first = Freshness(HARVEST, 14, date(2026, 11, 10))  # 5 days left
    last = Freshness(HARVEST, 14, date(2026, 11, 14))  # 1 day left
    found_first = policy.markdown(_listing(), first)
    found_last = policy.markdown(_listing(), last)
    assert found_first is not None and found_last is not None
    assert found_first.source is DiscountSource.CLEARANCE
    assert found_first.ends_on == date(2026, 11, 12)  # 20 % starts with 2 days left
    assert found_last.ends_on == date(2026, 11, 15)


def test_a_markdown_never_drops_the_farmers_share_under_the_minimum() -> None:
    # COP 1,600: the 80 % share holds while the farmer gets COP 1,500 or more.
    assert deepest_allowed(160_000, FEES, "COP", 35) == 6
    assert respects_share(shelf_price(160_000, FEES, "COP", 6), FEES)
    assert not respects_share(shelf_price(160_000, FEES, "COP", 7), FEES)
    assert _markdown_with_days_left("tomato", 0, price_minor=160_000) == 6
    assert _markdown_with_days_left("tomato", 0, price_minor=150_000) == 0


def test_the_ladder_must_deepen_as_life_runs_out(tmp_path: Path) -> None:
    raw = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8"))
    raw["clearance"]["steps"][1]["discount_pct"] = 5  # shallower than the step before
    broken = tmp_path / "market.yaml"
    broken.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_market_config(broken)


def test_without_steps_nothing_is_marked_down() -> None:
    config: MarketConfig = replace(load_market_config(CONFIG_FILE), clearance_steps=())
    fresh = Freshness(HARVEST, 14, date(2026, 11, 15))
    assert ClearancePolicy(config).markdown(_listing(), fresh) is None
