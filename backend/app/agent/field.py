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
    crop: str  # the catalogue key, e.g. "maize" (D077)
    crop_display: str
    root_depth_mm: float  # to size irrigation (D077)
    stage: str
    stage_display: str
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
    params: dict[str, float | str]
    rationale: str
    proposed_by: str


@dataclass(frozen=True)
class ProposalView:
    """The gate's answer as the agent sees it."""

    task_id: int
    status: str
    outcome: str
    effective_level: str
    reason: str | None  # the leading rule, in the farmer's words; None when allowed
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
    area: tuple[float, float, float, float]  # normalized (x1, y1, x2, y2) in the scene image


@dataclass(frozen=True)
class ImageryView:
    scene_id: str
    acquired_on: date
    synthetic: bool
    low_ndvi_threshold: float
    zones: tuple[ZoneImagery, ...]  # the plot's zones the scene covers
    segmentation_note: str | None  # why bare_soil_pct is missing, if it is
    boxes: tuple[tuple[float, float, float, float], ...]  # normalized SAM boxes; () when unknown

    def low_vigor(self, zone: ZoneImagery) -> bool:
        """Mean NDVI strictly below the threshold; an unknown mean is not low (D059)."""
        return zone.ndvi_mean is not None and zone.ndvi_mean < self.low_ndvi_threshold


class ImageryReader(Protocol):
    def imagery(self, plot_id: int, day: date) -> ImageryView | None: ...  # None: no scene
    def scene_png(self, plot_id: int, day: date) -> bytes | None: ...  # None: no scene


# --- D093: what the agronomist and its two specialists read and change -----------------


@dataclass(frozen=True)
class Microclimate:
    """A zone's air over a window, from its temperature and humidity sensors."""

    zone_id: int
    window_hours: float
    readings: int  # how many paired readings the window holds; 0: nothing to say
    temperature_mean_c: float | None
    temperature_max_c: float | None
    humidity_mean_pct: float | None
    humidity_max_pct: float | None
    humid_leaf_hours: float | None  # RH >= 90 % between 10 and 30 °C
    last_reading_id: int | None  # the latest humidity reading, for the observation id
    until: datetime


@dataclass(frozen=True)
class SoilTarget:
    low: float
    high: float


@dataclass(frozen=True)
class SoilView:
    """A zone's soil: measured or estimated values and the crop's target ranges."""

    zone_id: int
    ph: float
    ph_source: str  # "soilgrids" or "probe"
    organic_carbon_g_kg: float | None
    nitrogen_ppm: float
    phosphorus_ppm: float
    potassium_ppm: float
    targets: dict[str, SoilTarget]  # by "ph", "nitrogen", "phosphorus", "potassium"
    simulated: bool  # the N-P-K probe is simulated (D038, D093)


@dataclass(frozen=True)
class TaskRecord:
    task_id: int
    action_type: str
    zone_id: int | None
    scheduled_for: datetime
    status: str
    proposed_by: str
    params: dict[str, float | str]
    rationale: str


class Agronomy(Protocol):
    """The agronomist's view beyond water, and its one way to withdraw a task (D093)."""

    def microclimate(self, plot_id: int, zone_id: int, at: datetime) -> Microclimate | None: ...
    def soil(self, plot_id: int, zone_id: int, at: datetime) -> SoilView | None: ...
    def open_tasks(self, plot_id: int) -> Sequence[TaskRecord]: ...
    def cancel(self, plot_id: int, task_id: int, reason: str, actor: str) -> TaskRecord: ...


class TaskNotCancellableError(Exception):
    """The task is not this plot's, not an agent's, or has already run. Told to the model."""
