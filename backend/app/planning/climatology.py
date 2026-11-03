"""B0: the FAO oracle on the climatology, served when no adopted network exists (D079)."""

from collections.abc import Sequence
from datetime import date

from fieldpilot_planner.crops import CropCard
from fieldpilot_planner.serving import SiteSnapshot, climatology_plan, decode_b0

from app.planning.ports import Recommendation

B0_MODEL_ID = "b0-climatology"


class ClimatologyRecommender:
    def __init__(
        self, crops: Sequence[CropCard], success_threshold: float, spinup_days: int
    ) -> None:
        self._crops = tuple(crops)
        self._success_threshold = success_threshold
        self._spinup_days = spinup_days

    @property
    def model_id(self) -> str:
        return B0_MODEL_ID

    @property
    def crops(self) -> Sequence[CropCard]:
        return self._crops

    def recommend(self, snapshot: SiteSnapshot, sowing_dates: Sequence[date]) -> Recommendation:
        plan = climatology_plan(
            snapshot, sowing_dates, self._crops, self._success_threshold, self._spinup_days
        )
        return Recommendation(plan.contexts, decode_b0(plan))
