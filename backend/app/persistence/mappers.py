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
    PlanAtSowing,
    Plot,
    Reading,
    Report,
    Sensor,
    SimClockState,
    Stage,
    Task,
    Zone,
)
from app.identity.models import AuthEvent, AuthEventKind, Phone, RefreshSession, Role, User
from app.persistence.tables import (
    AuthEventRow,
    ControlStateRow,
    CropCycleRow,
    DecisionRow,
    EventRow,
    NotificationRow,
    PlotRow,
    ReadingRow,
    RefreshSessionRow,
    ReportRow,
    SensorRow,
    SimClockStateRow,
    StageRow,
    TaskRow,
    UserRow,
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
        utc_offset_hours=plot.utc_offset_hours,
        municipality=plot.municipality,
        department=plot.department,
    )


def plot_from_row(row: PlotRow) -> Plot:
    return Plot(
        id=row.id,
        name=row.name,
        latitude=row.latitude,
        longitude=row.longitude,
        area_ha=row.area_ha,
        created_at=row.created_at,
        utc_offset_hours=row.utc_offset_hours,
        municipality=row.municipality,
        department=row.department,
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
        gdd_updated_through=cycle.gdd_updated_through,
        status=cycle.status,
        automated=cycle.automated,
        own_risk=cycle.own_risk,
        plan_model=None if cycle.plan is None else cycle.plan.model,
        plan_rank=None if cycle.plan is None else cycle.plan.rank,
        plan_rel_yield_p50=None if cycle.plan is None else cycle.plan.rel_yield_p50,
        plan_p_success=None if cycle.plan is None else cycle.plan.p_success,
        harvested_on=cycle.harvested_on,
    )


def cycle_from_row(row: CropCycleRow) -> CropCycle:
    return CropCycle(
        id=row.id,
        plot_id=row.plot_id,
        crop=row.crop,
        sowing_date=row.sowing_date,
        accumulated_gdd=row.accumulated_gdd,
        gdd_updated_through=row.gdd_updated_through,
        status=CycleStatus(row.status),
        automated=row.automated,
        own_risk=row.own_risk,
        plan=_plan_from_row(row),
        harvested_on=row.harvested_on,
    )


def _plan_from_row(row: CropCycleRow) -> PlanAtSowing | None:
    if (
        row.plan_model is None
        or row.plan_rank is None
        or row.plan_rel_yield_p50 is None
        or row.plan_p_success is None
    ):
        return None
    return PlanAtSowing(row.plan_model, row.plan_rank, row.plan_rel_yield_p50, row.plan_p_success)


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


def user_to_row(user: User) -> UserRow:
    return UserRow(
        id=user.id,
        phone=user.phone.e164,
        full_name=user.full_name,
        role=user.role.value,
        password_hash=user.password_hash,
        active=user.active,
        failed_logins=user.failed_logins,
        locked_until=user.locked_until,
        last_login_at=user.last_login_at,
        consent_version=user.consent_version,
        consent_at=user.consent_at,
        created_at=user.created_at,
    )


def user_from_row(row: UserRow) -> User:
    return User(
        id=row.id,
        phone=Phone(row.phone),
        full_name=row.full_name,
        role=Role(row.role),
        password_hash=row.password_hash,
        active=row.active,
        failed_logins=row.failed_logins,
        locked_until=row.locked_until,
        last_login_at=row.last_login_at,
        consent_version=row.consent_version,
        consent_at=row.consent_at,
        created_at=row.created_at,
    )


def refresh_session_to_row(session: RefreshSession) -> RefreshSessionRow:
    return RefreshSessionRow(
        id=session.id,
        user_id=session.user_id,
        token_hash=session.token_hash,
        family_id=session.family_id,
        expires_at=session.expires_at,
        created_at=session.created_at,
        used_at=session.used_at,
        revoked_at=session.revoked_at,
    )


def refresh_session_from_row(row: RefreshSessionRow) -> RefreshSession:
    return RefreshSession(
        id=row.id,
        user_id=row.user_id,
        token_hash=row.token_hash,
        family_id=row.family_id,
        expires_at=row.expires_at,
        created_at=row.created_at,
        used_at=row.used_at,
        revoked_at=row.revoked_at,
    )


def auth_event_to_row(event: AuthEvent) -> AuthEventRow:
    return AuthEventRow(
        id=event.id,
        occurred_at=event.occurred_at,
        kind=event.kind.value,
        user_id=event.user_id,
        detail=dict(event.detail),
    )


def auth_event_from_row(row: AuthEventRow) -> AuthEvent:
    return AuthEvent(
        id=row.id,
        occurred_at=row.occurred_at,
        kind=AuthEventKind(row.kind),
        user_id=row.user_id,
        detail=row.detail,
    )
