"""Conversions between table rows and domain objects."""

from typing import Any

from app.domain.enums import (
    ActionType,
    AutonomyLevel,
    CycleStatus,
    EventKind,
    GateOutcome,
    SensorKind,
    TaskStatus,
)
from app.domain.models import (
    ControlState,
    CropCycle,
    Decision,
    Event,
    Money,
    Notification,
    Plot,
    Reading,
    Report,
    Sensor,
    SimClockState,
    Stage,
    Task,
    Zone,
)
from app.persistence.tables import (
    ControlStateRow,
    CropCycleRow,
    DecisionRow,
    EventRow,
    NotificationRow,
    PlotRow,
    ReadingRow,
    ReportRow,
    SensorRow,
    SimClockStateRow,
    StageRow,
    TaskRow,
    ZoneRow,
)


def plot_to_row(plot: Plot) -> PlotRow:
    return PlotRow(
        id=plot.id,
        name=plot.name,
        latitude=plot.latitude,
        longitude=plot.longitude,
        area_ha=plot.area_ha,
        created_at=plot.created_at,
    )


def plot_from_row(row: PlotRow) -> Plot:
    return Plot(
        id=row.id,
        name=row.name,
        latitude=row.latitude,
        longitude=row.longitude,
        area_ha=row.area_ha,
        created_at=row.created_at,
    )


def zone_to_row(zone: Zone) -> ZoneRow:
    return ZoneRow(
        id=zone.id,
        plot_id=zone.plot_id,
        name=zone.name,
        area_ha=zone.area_ha,
        field_capacity_pct=zone.field_capacity_pct,
        valve_id=zone.valve_id,
    )


def zone_from_row(row: ZoneRow) -> Zone:
    return Zone(
        id=row.id,
        plot_id=row.plot_id,
        name=row.name,
        area_ha=row.area_ha,
        field_capacity_pct=row.field_capacity_pct,
        valve_id=row.valve_id,
    )


def sensor_to_row(sensor: Sensor) -> SensorRow:
    return SensorRow(id=sensor.id, zone_id=sensor.zone_id, kind=sensor.kind, unit=sensor.unit)


def sensor_from_row(row: SensorRow) -> Sensor:
    return Sensor(id=row.id, zone_id=row.zone_id, kind=SensorKind(row.kind), unit=row.unit)


def reading_to_row(reading: Reading) -> ReadingRow:
    return ReadingRow(
        id=reading.id,
        sensor_id=reading.sensor_id,
        value=reading.value,
        recorded_at=reading.recorded_at,
    )


def reading_from_row(row: ReadingRow) -> Reading:
    return Reading(id=row.id, sensor_id=row.sensor_id, value=row.value, recorded_at=row.recorded_at)


def cycle_to_row(cycle: CropCycle) -> CropCycleRow:
    return CropCycleRow(
        id=cycle.id,
        plot_id=cycle.plot_id,
        crop=cycle.crop,
        sowing_date=cycle.sowing_date,
        accumulated_gdd=cycle.accumulated_gdd,
        status=cycle.status,
    )


def cycle_from_row(row: CropCycleRow) -> CropCycle:
    return CropCycle(
        id=row.id,
        plot_id=row.plot_id,
        crop=row.crop,
        sowing_date=row.sowing_date,
        accumulated_gdd=row.accumulated_gdd,
        status=CycleStatus(row.status),
    )


def stage_to_row(stage: Stage) -> StageRow:
    return StageRow(
        id=stage.id,
        cycle_id=stage.cycle_id,
        name=stage.name,
        started_at=stage.started_at,
        ended_at=stage.ended_at,
        gdd_at_start=stage.gdd_at_start,
    )


def stage_from_row(row: StageRow) -> Stage:
    return Stage(
        id=row.id,
        cycle_id=row.cycle_id,
        name=row.name,
        started_at=row.started_at,
        ended_at=row.ended_at,
        gdd_at_start=row.gdd_at_start,
    )


def task_to_row(task: Task) -> TaskRow:
    cost = task.estimated_cost
    return TaskRow(
        id=task.id,
        cycle_id=task.cycle_id,
        zone_id=task.zone_id,
        action_type=task.action_type,
        params=dict(task.params),
        scheduled_for=task.scheduled_for,
        status=task.status,
        effective_level=task.effective_level,
        rationale=task.rationale,
        estimated_cost_minor=cost.amount_minor if cost else None,
        estimated_cost_currency=cost.currency if cost else None,
        revert_deadline=task.revert_deadline,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def task_from_row(row: TaskRow) -> Task:
    cost = None
    if row.estimated_cost_minor is not None and row.estimated_cost_currency is not None:
        cost = Money(row.estimated_cost_minor, row.estimated_cost_currency)
    return Task(
        id=row.id,
        cycle_id=row.cycle_id,
        zone_id=row.zone_id,
        action_type=ActionType(row.action_type),
        params=dict(row.params),
        scheduled_for=row.scheduled_for,
        status=TaskStatus(row.status),
        effective_level=AutonomyLevel(row.effective_level),
        rationale=row.rationale,
        estimated_cost=cost,
        revert_deadline=row.revert_deadline,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def decision_to_row(decision: Decision) -> DecisionRow:
    return DecisionRow(
        id=decision.id,
        task_id=decision.task_id,
        requested_level=decision.requested_level,
        effective_level=decision.effective_level,
        outcome=decision.outcome,
        violations=[dict(v) for v in decision.violations],
        reason=decision.reason,
        inputs=dict(decision.inputs),
        created_at=decision.created_at,
    )


def decision_from_row(row: DecisionRow) -> Decision:
    return Decision(
        id=row.id,
        task_id=row.task_id,
        requested_level=AutonomyLevel(row.requested_level),
        effective_level=AutonomyLevel(row.effective_level),
        outcome=GateOutcome(row.outcome),
        violations=tuple(row.violations),
        reason=row.reason,
        inputs=dict(row.inputs),
        created_at=row.created_at,
    )


def event_to_row(event: Event) -> EventRow:
    return EventRow(
        id=event.id,
        occurred_at=event.occurred_at,
        kind=event.kind,
        actor=event.actor,
        task_id=event.task_id,
        decision_id=event.decision_id,
        autonomy_level=event.autonomy_level,
        rule=event.rule,
        reason=event.reason,
        inputs=dict(event.inputs),
        idempotency_key=event.idempotency_key,
    )


def event_from_row(row: EventRow) -> Event:
    return Event(
        id=row.id,
        occurred_at=row.occurred_at,
        kind=EventKind(row.kind),
        actor=row.actor,
        task_id=row.task_id,
        decision_id=row.decision_id,
        autonomy_level=_optional_level(row.autonomy_level),
        rule=row.rule,
        reason=row.reason,
        inputs=dict(row.inputs),
        idempotency_key=row.idempotency_key,
    )


def notification_to_row(notification: Notification) -> NotificationRow:
    return NotificationRow(
        id=notification.id,
        task_id=notification.task_id,
        message=notification.message,
        created_at=notification.created_at,
        read_at=notification.read_at,
        revert_deadline=notification.revert_deadline,
    )


def notification_from_row(row: NotificationRow) -> Notification:
    return Notification(
        id=row.id,
        task_id=row.task_id,
        message=row.message,
        created_at=row.created_at,
        read_at=row.read_at,
        revert_deadline=row.revert_deadline,
    )


def report_to_row(report: Report) -> ReportRow:
    return ReportRow(
        id=report.id,
        cycle_id=report.cycle_id,
        stage_id=report.stage_id,
        language=report.language,
        content=report.content,
        created_at=report.created_at,
    )


def report_from_row(row: ReportRow) -> Report:
    return Report(
        id=row.id,
        cycle_id=row.cycle_id,
        stage_id=row.stage_id,
        language=row.language,
        content=row.content,
        created_at=row.created_at,
    )


def control_state_from_row(row: ControlStateRow) -> ControlState:
    return ControlState(
        emergency_stop_active=row.emergency_stop_active,
        changed_at=row.changed_at,
        changed_by=row.changed_by,
    )


def sim_clock_from_row(row: SimClockStateRow) -> SimClockState:
    return SimClockState(
        sim_anchor=row.sim_anchor,
        wall_anchor=row.wall_anchor,
        speed_factor=row.speed_factor,
        paused=row.paused,
    )


def _optional_level(value: Any) -> AutonomyLevel | None:
    return AutonomyLevel(value) if value is not None else None
