"""Load and validate config/market.yaml (D085)."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.errors import ConfigError


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _Fees(_Strict):
    logistics_per_kg: float = Field(ge=0)
    platform_pct: float = Field(ge=0, lt=100)
    min_farmer_share_pct: float = Field(gt=0, le=100)


class _Offers(_Strict):
    max_discount_pct: int = Field(gt=0, lt=100)
    max_days: int = Field(gt=0)


class _Warehouse(_Strict):
    code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    municipality: str
    department: str
    cold_storage: bool


class _Recommender(_Strict):
    weights: dict[str, float]
    due_ratio: float = Field(gt=0)
    fresh_days: int = Field(gt=0)


class _MarketFile(_Strict):
    currency: str = Field(min_length=3, max_length=3)
    fees: _Fees
    offers: _Offers
    warehouses: list[_Warehouse] = Field(min_length=1)
    shelf_life_days: dict[str, int]
    recommender: _Recommender


@dataclass(frozen=True)
class MarketFees:
    logistics_per_kg: float
    platform_pct: float
    min_farmer_share_pct: float


@dataclass(frozen=True)
class WarehouseSpec:
    code: str
    name: str
    municipality: str
    department: str
    cold_storage: bool


@dataclass(frozen=True)
class MarketConfig:
    currency: str
    fees: MarketFees
    max_discount_pct: int
    max_offer_days: int
    warehouses: tuple[WarehouseSpec, ...]  # the first is the default
    shelf_life_days: Mapping[str, int]
    weights: Mapping[str, float]
    due_ratio: float
    fresh_days: int


REQUIRED_WEIGHTS = frozenset(
    {"repurchase_due", "bought_together", "fresh_harvest", "on_offer", "popular"}
)


def load_market_config(path: Path) -> MarketConfig:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        parsed = _MarketFile.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise ConfigError(f"{path.name}: {error}") from error
    missing = REQUIRED_WEIGHTS - set(parsed.recommender.weights)
    if missing:
        raise ConfigError(f"{path.name}: recommender weights missing {sorted(missing)}")
    return MarketConfig(
        currency=parsed.currency,
        fees=MarketFees(**parsed.fees.model_dump()),
        max_discount_pct=parsed.offers.max_discount_pct,
        max_offer_days=parsed.offers.max_days,
        warehouses=tuple(WarehouseSpec(**w.model_dump()) for w in parsed.warehouses),
        shelf_life_days=parsed.shelf_life_days,
        weights=parsed.recommender.weights,
        due_ratio=parsed.recommender.due_ratio,
        fresh_days=parsed.recommender.fresh_days,
    )
