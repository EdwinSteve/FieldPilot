"""Load and validate config/market.yaml (D085)."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

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


class _ClearanceStep(_Strict):
    life_left_pct: int = Field(gt=0, lt=100)
    discount_pct: int = Field(gt=0, lt=100)


class _Clearance(_Strict):
    steps: list[_ClearanceStep]

    @model_validator(mode="after")
    def _a_ladder(self) -> "_Clearance":
        """Less life left, a deeper discount: each step goes further than the last."""
        for before, after in zip(self.steps, self.steps[1:], strict=False):
            if not (after.life_left_pct < before.life_left_pct
                    and after.discount_pct > before.discount_pct):  # fmt: skip
                raise ValueError("clearance steps must go down in life left and up in discount")
        return self


class _MarketFile(_Strict):
    currency: str = Field(min_length=3, max_length=3)
    fees: _Fees
    offers: _Offers
    warehouses: list[_Warehouse] = Field(min_length=1)
    shelf_life_days: dict[str, int]
    clearance: _Clearance
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
class ClearanceStep:
    life_left_pct: int
    discount_pct: int


@dataclass(frozen=True)
class MarketConfig:
    currency: str
    fees: MarketFees
    max_discount_pct: int
    max_offer_days: int
    warehouses: tuple[WarehouseSpec, ...]  # the first is the default
    shelf_life_days: Mapping[str, int]
    clearance_steps: tuple[ClearanceStep, ...]  # most life left first (D086)
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
        clearance_steps=tuple(ClearanceStep(**s.model_dump()) for s in parsed.clearance.steps),
        weights=parsed.recommender.weights,
        due_ratio=parsed.recommender.due_ratio,
        fresh_days=parsed.recommender.fresh_days,
    )
