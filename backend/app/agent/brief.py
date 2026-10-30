"""What the agent may cite, and what one subagent hands to the next (D044, D050).

Read tools record every value they return in the `ObservationLedger`. The
closing tools check citations against it, as the workshop checks quotes
against the page.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import StrEnum


class ObservationKind(StrEnum):
    SOIL_MOISTURE = "soil_moisture"
    FIELD_CAPACITY = "field_capacity"
    RAIN_FORECAST = "rain_forecast"
    GDD = "gdd"
    KC = "kc"
    STAGE = "stage"
    IRRIGATION = "irrigation"


@dataclass(frozen=True)
class Observation:
    id: str
    kind: ObservationKind
    zone_id: int | None
    value: float | str | None  # None: the source cannot say (e.g. an unknown forecast)
    unit: str  # "%", "mm", "GDD", or "" for none
    at: datetime | None  # None for a static fact (field capacity, stage of the run)


class ObservationConflictError(Exception):
    """The same observation id was recorded with different content. A bug, never data."""


class ObservationLedger:
    """The observations of one daily cycle or chat turn. In memory only."""

    def __init__(self) -> None:
        self._observations: dict[str, Observation] = {}

    def add(self, observation: Observation) -> Observation:
        """Record an observation. Re-reading the same value is fine; a changed one is not."""
        known = self._observations.get(observation.id)
        if known is not None and known != observation:
            raise ObservationConflictError(f"observation {observation.id} changed within a run")
        self._observations[observation.id] = observation
        return observation

    def get(self, observation_id: str) -> Observation | None:
        return self._observations.get(observation_id)

    def __len__(self) -> int:
        return len(self._observations)


@dataclass(frozen=True)
class ZoneAssessment:
    zone_id: int
    status: str  # dry | ok | wet
    moisture_pct: float | None
    cited: tuple[str, ...]


@dataclass(frozen=True)
class Assessment:
    zones: tuple[ZoneAssessment, ...]
    summary: str


@dataclass(frozen=True)
class ProposalSummary:
    task_id: int
    action_type: str
    zone_id: int | None
    outcome: str  # the gate outcome
    effective_level: str
    status: str  # the task status right after the proposal


@dataclass(frozen=True)
class FieldBrief:
    """The structured handoff between subagents. Never free text (D044)."""

    plot_id: int
    day: date
    assessment: Assessment | None = None
    proposals: tuple[ProposalSummary, ...] = field(default_factory=tuple)

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str, sort_keys=True)


class BriefDraft:
    """The brief while a cycle builds it. Closing tools fill it; `freeze` hands it on.

    In memory only: filling it is not a write in the D054 sense.
    """

    def __init__(self, plot_id: int, day: date) -> None:
        self.plot_id = plot_id
        self.day = day
        self.assessment: Assessment | None = None
        self.proposals: list[ProposalSummary] = []

    def freeze(self) -> FieldBrief:
        return FieldBrief(self.plot_id, self.day, self.assessment, tuple(self.proposals))
