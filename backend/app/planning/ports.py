"""Interfaces the planning service depends on (§4.11, D081)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from fieldpilot_planner.crops import CropCard
from fieldpilot_planner.serving import PlanOutputs, SiteSnapshot, SowingContext

from app.domain.models import Plot


@dataclass(frozen=True)
class SiteRecord:
    snapshot: SiteSnapshot
    sha256: str  # of the stored snapshot: each plan can be traced to its data


class SiteSource(Protocol):
    def site(self, plot: Plot) -> SiteRecord: ...  # MissingDataError when none matches the plot


@dataclass(frozen=True)
class Recommendation:
    contexts: tuple[SowingContext, ...]  # one per sowing date
    outputs: PlanOutputs  # [N dates, C crops]


class CropRecommender(Protocol):
    @property
    def model_id(self) -> str: ...
    @property
    def crops(self) -> Sequence[CropCard]: ...
    def recommend(self, snapshot: SiteSnapshot, sowing_dates: Sequence[date]) -> Recommendation:
        """IncompleteHistoryError when the snapshot cannot cover a date."""
        ...
