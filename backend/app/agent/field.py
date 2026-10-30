"""The read-only view of the field the agent sees, behind a port (§4.8).

`app/agent` never touches persistence; `app/services/field_reader.py`
implements this port over the unit of work.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
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
