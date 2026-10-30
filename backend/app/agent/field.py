"""The read-only view of the field the agent sees, behind a port (§4.8).

`app/agent` never touches persistence; `app/services/field_reader.py`
implements this port over the unit of work.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


@dataclass(frozen=True)
class MoistureReading:
    reading_id: int
    value_pct: float
    recorded_at: datetime


@dataclass(frozen=True)
class IrrigationRecord:
    task_id: int
    action_type: str
    volume_mm: float
    scheduled_for: datetime
    status: str


@dataclass(frozen=True)
class ZoneView:
    zone_id: int
    name: str
    field_capacity_pct: float
    moisture: MoistureReading | None
    last_irrigation: IrrigationRecord | None  # the latest executed one, if any
    upcoming: tuple[IrrigationRecord, ...]  # scheduled or awaiting approval


@dataclass(frozen=True)
class StageView:
    cycle_id: int
    stage: str
    stage_display_es: str
    accumulated_gdd: float
    kc: float


class FieldReader(Protocol):
    def zones(self, plot_id: int) -> Sequence[ZoneView]: ...
    def zone(self, plot_id: int, zone_id: int) -> ZoneView | None: ...  # None: not in this plot
    def rain_mm_next_24h(self, plot_id: int, at: datetime) -> float | None: ...
    def crop_stage(self, plot_id: int) -> StageView: ...
    def task_status(self, plot_id: int, task_id: int) -> str | None: ...  # None: not this plot's


@dataclass(frozen=True)
class ActionRequest:
    """What propose_action asks for. The adapter turns it into a `ProposedAction`."""

    action_type: str
    plot_id: int
    zone_id: int | None
    scheduled_for: datetime
    params: dict[str, float]
    rationale: str
    proposed_by: str


@dataclass(frozen=True)
class ProposalView:
    """The gate's answer as the agent sees it."""

    task_id: int
    status: str
    outcome: str
    effective_level: str
    reason_es: str | None  # the leading rule, in the farmer's words; None when allowed
    already_decided: bool


class ActionProposer(Protocol):
    """The agent's only way to change anything: through ProposalService and the gate."""

    def propose(self, request: ActionRequest) -> ProposalView: ...


class FarmerOutbox(Protocol):
    """What reaches the farmer: verified reports and catalogue notifications (D052)."""

    def save_report(self, plot_id: int, text_es: str) -> int: ...
    def notify(self, plot_id: int, text_key: str) -> None: ...


@dataclass(frozen=True)
class ZoneImagery:
    zone_id: int
    ndvi_mean: float | None
    low_ndvi_pct: float | None
    bare_soil_pct: float | None  # None when segmentation was unavailable


@dataclass(frozen=True)
class ImageryView:
    scene_id: str
    acquired_on: date
    synthetic: bool
    low_ndvi_threshold: float
    zones: tuple[ZoneImagery, ...]  # the plot's zones the scene covers
    segmentation_note: str | None  # why bare_soil_pct is missing, if it is


class ImageryReader(Protocol):
    def imagery(self, plot_id: int, day: date) -> ImageryView | None: ...  # None: no scene
