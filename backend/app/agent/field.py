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
