"""Lot and trace value objects. Quantities are integer grams; datetimes aware UTC."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum

from app.domain.models import JsonValue

GENESIS_HASH = "0" * 64


class Grade(StrEnum):
    EXTRA = "extra"
    FIRST = "first"
    SECOND = "second"


class BizStep(StrEnum):
    """GS1 EPCIS 2.0 business steps; shipping, receiving and selling come later (D080)."""

    COMMISSIONING = "commissioning"


@dataclass(frozen=True)
class HarvestLot:
    code: str  # FP-<plot>-<yyyymmdd>-<n>, printed in the QR
    cycle_id: int
    plot_id: int
    crop: str
    harvested_on: date
    quantity_g: int
    grade: Grade
    created_at: datetime

    @property
    def quantity_kg(self) -> float:
        return self.quantity_g / 1000


@dataclass(frozen=True)
class TraceEvent:
    lot_code: str
    seq: int  # 0 is the commissioning
    biz_step: BizStep
    occurred_at: datetime
    actor: str
    quantity_g: int
    prev_hash: str
    hash: str
    data: Mapping[str, JsonValue] = field(default_factory=dict)
    id: int | None = None
