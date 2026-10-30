"""Request and response bodies. Mapping from domain objects only; no logic."""

import json
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, JsonValue

from app.agent.loop import AgentRun
from app.domain.enums import ActionType, AutonomyLevel, EventKind, TaskStatus
from app.domain.models import (
    ControlState,
    Event,
    Notification,
    Plot,
    Reading,
    Report,
    Stage,
    Zone,
)
from app.services.daily_cycle import DailyCycleResult
from app.services.queries import CycleView, SensorReadings, TaskView
from app.services.ticker import TickResult


class PlotOut(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    area_ha: float
    utc_offset_hours: float

    @classmethod
    def of(cls, plot: Plot) -> "PlotOut":
        return cls(
            id=_id(plot.id),
            name=plot.name,
            latitude=plot.latitude,
            longitude=plot.longitude,
            area_ha=plot.area_ha,
            utc_offset_hours=plot.utc_offset_hours,
        )


class ZoneOut(BaseModel):
    id: int
    plot_id: int
    name: str
    area_ha: float
    field_capacity_pct: float

    @classmethod
    def of(cls, zone: Zone) -> "ZoneOut":
        return cls(
            id=_id(zone.id),
            plot_id=zone.plot_id,
            name=zone.name,
            area_ha=zone.area_ha,
            field_capacity_pct=zone.field_capacity_pct,
        )


class ReadingOut(BaseModel):
    value: float
    recorded_at: datetime

    @classmethod
    def of(cls, reading: Reading) -> "ReadingOut":
        return cls(value=reading.value, recorded_at=reading.recorded_at)


class SensorReadingsOut(BaseModel):
    sensor_id: int
    kind: str
    unit: str
    readings: list[ReadingOut]

    @classmethod
    def of(cls, view: SensorReadings) -> "SensorReadingsOut":
        return cls(
            sensor_id=_id(view.sensor.id),
            kind=str(view.sensor.kind),
            unit=view.sensor.unit,
            readings=[ReadingOut.of(r) for r in view.readings],
        )


class StageOut(BaseModel):
    name: str
    started_at: datetime
    ended_at: datetime | None
    gdd_at_start: float

    @classmethod
    def of(cls, stage: Stage) -> "StageOut":
        return cls(
            name=stage.name,
            started_at=stage.started_at,
            ended_at=stage.ended_at,
            gdd_at_start=stage.gdd_at_start,
        )


class CycleOut(BaseModel):
    id: int
    plot_id: int
    crop: str
    sowing_date: date
    status: str
    accumulated_gdd: float
    gdd_updated_through: date | None
    stages: list[StageOut]

    @classmethod
    def of(cls, view: CycleView) -> "CycleOut":
        cycle = view.cycle
        return cls(
            id=_id(cycle.id),
            plot_id=cycle.plot_id,
            crop=cycle.crop,
            sowing_date=cycle.sowing_date,
            status=str(cycle.status),
            accumulated_gdd=cycle.accumulated_gdd,
            gdd_updated_through=cycle.gdd_updated_through,
            stages=[StageOut.of(s) for s in view.stages],
        )


class TaskOut(BaseModel):
    id: int
    cycle_id: int
    zone_id: int | None
    action_type: ActionType
    params: dict[str, JsonValue]
    scheduled_for: datetime
    status: TaskStatus
    effective_level: AutonomyLevel
    rationale: str
    created_at: datetime
    updated_at: datetime
    # D011: the backend decides; the UI only displays.
    revert_deadline: datetime | None
    revert_open: bool | None
    revert_remaining_seconds: float | None

    @classmethod
    def of(cls, view: TaskView) -> "TaskOut":
        task = view.task
        remaining = view.revert_remaining
        return cls(
            id=_id(task.id),
            cycle_id=task.cycle_id,
            zone_id=task.zone_id,
            action_type=task.action_type,
            params=dict(task.params),
            scheduled_for=task.scheduled_for,
            status=task.status,
            effective_level=task.effective_level,
            rationale=task.rationale,
            created_at=task.created_at,
            updated_at=task.updated_at,
            revert_deadline=task.revert_deadline,
            revert_open=view.revert_open,
            revert_remaining_seconds=None if remaining is None else remaining.total_seconds(),
        )


class RevertOut(BaseModel):
    task: TaskOut
    requested_mm: float
    applied_mm: float
    applied_liters: float


class RejectIn(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class EventOut(BaseModel):
    id: int
    kind: EventKind
    actor: str
    reason: str
    occurred_at: datetime
    task_id: int | None
    autonomy_level: AutonomyLevel | None
    rule: str | None
    inputs: dict[str, JsonValue]

    @classmethod
    def of(cls, event: Event) -> "EventOut":
        return cls(
            id=_id(event.id),
            kind=event.kind,
            actor=event.actor,
            reason=event.reason,
            occurred_at=event.occurred_at,
            task_id=event.task_id,
            autonomy_level=event.autonomy_level,
            rule=event.rule,
            inputs=dict(event.inputs),
        )


class NotificationOut(BaseModel):
    id: int
    message: str
    created_at: datetime
    task_id: int | None
    read_at: datetime | None
    revert_deadline: datetime | None

    @classmethod
    def of(cls, note: Notification) -> "NotificationOut":
        return cls(
            id=_id(note.id),
            message=note.message,
            created_at=note.created_at,
            task_id=note.task_id,
            read_at=note.read_at,
            revert_deadline=note.revert_deadline,
        )


class ReportOut(BaseModel):
    id: int
    cycle_id: int
    language: str
    content: str
    created_at: datetime

    @classmethod
    def of(cls, report: Report) -> "ReportOut":
        return cls(
            id=_id(report.id),
            cycle_id=report.cycle_id,
            language=report.language,
            content=report.content,
            created_at=report.created_at,
        )


class ChatIn(BaseModel):
    plot_id: int
    question: str = Field(min_length=1, max_length=2000)


class ChatOut(BaseModel):
    run_id: str
    status: str
    answer: str | None  # verified by answer_farmer (D053); None unless completed
    turns: int

    @classmethod
    def of(cls, run: AgentRun) -> "ChatOut":
        output = run.output
        answer = output.get("answer") if isinstance(output, dict) else None
        return cls(
            run_id=run.run_id,
            status=str(run.status),
            answer=answer if isinstance(answer, str) else None,
            turns=run.turns,
        )


class VoiceOut(ChatOut):
    transcript: str  # what was understood, shown to the farmer (D061)


class DailyCycleIn(BaseModel):
    plot_id: int


class RunOut(BaseModel):
    run_id: str
    subagent: str
    status: str
    turns: int


class DailyCycleOut(BaseModel):
    session_id: str
    status: str
    stopped_at: str | None
    runs: list[RunOut]
    brief: dict[str, JsonValue]

    @classmethod
    def of(cls, result: DailyCycleResult) -> "DailyCycleOut":
        brief: dict[str, JsonValue] = json.loads(result.brief.to_json())
        return cls(
            session_id=result.session_id,
            status=str(result.status),
            stopped_at=result.stopped_at,
            runs=[
                RunOut(run_id=r.run_id, subagent=r.subagent, status=str(r.status), turns=r.turns)
                for r in result.runs
            ],
            brief=brief,
        )


class ClockOut(BaseModel):
    now: datetime
    speed_factor: float
    paused: bool


class ClockIn(BaseModel):
    action: Literal["pause", "resume", "speed", "advance"]
    speed_factor: float | None = Field(default=None, gt=0, le=10_000)
    advance_seconds: float | None = Field(default=None, ge=0, le=60 * 60 * 24 * 30)


class TickOut(BaseModel):
    at: datetime
    readings_recorded: int
    tasks: list[TaskOut]
    days_counted: list[date]
    zones_without_data: list[int]

    @classmethod
    def of(cls, result: TickResult, tasks: list[TaskOut]) -> "TickOut":
        return cls(
            at=result.at,
            readings_recorded=result.readings_recorded,
            tasks=tasks,
            days_counted=list(result.days_counted),
            zones_without_data=list(result.zones_without_data),
        )


class EmergencyStopIn(BaseModel):
    active: bool


class EmergencyStopOut(BaseModel):
    active: bool
    changed_at: datetime | None
    changed_by: str | None

    @classmethod
    def of(cls, state: ControlState) -> "EmergencyStopOut":
        return cls(
            active=state.emergency_stop_active,
            changed_at=state.changed_at,
            changed_by=state.changed_by,
        )


def _id(value: int | None) -> int:
    if value is None:
        raise ValueError("an unsaved entity cannot be returned")
    return value
