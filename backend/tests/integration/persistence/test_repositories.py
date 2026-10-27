"""Round trips through SQLite for every repository."""

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import StatementError

from app.domain.enums import (
    AutonomyLevel,
    CycleStatus,
    EventKind,
    GateOutcome,
    SensorKind,
    TaskStatus,
)
from app.domain.errors import NotFoundError
from app.domain.models import (
    Decision,
    Money,
    Notification,
    Plot,
    Reading,
    Report,
    Sensor,
    SimClockState,
    Stage,
)
from app.persistence.unit_of_work import SqlUnitOfWork
from tests.conftest import T0, FieldIds, later, make_event, make_task

UowFactory = Callable[[], SqlUnitOfWork]
BOGOTA = timezone(timedelta(hours=-5))


def test_plot_and_zone_round_trip(uow: UowFactory, field: FieldIds) -> None:
    with uow() as u:
        plot = u.plots.get(field.plot_id)
        zones = u.zones.list_by_plot(field.plot_id)

    assert plot.name == "Demo farm"
    assert [z.name for z in zones] == ["Zone 2"]
    assert zones[0].area_m2 == 5_000


def test_missing_entity_raises_not_found(uow: UowFactory) -> None:
    with uow() as u, pytest.raises(NotFoundError, match="Plot 42"):
        u.plots.get(42)


def test_readings_latest_and_range(uow: UowFactory, field: FieldIds) -> None:
    with uow() as u:
        sensor = u.sensors.add(Sensor(field.zone_id, SensorKind.SOIL_MOISTURE, "%"))
        assert sensor.id is not None
        u.readings.add_many(
            [Reading(sensor.id, 38.0, later(0)), Reading(sensor.id, 21.0, later(60))]
        )
        u.commit()

    with uow() as u:
        latest = u.readings.latest(sensor.id)
        early = u.readings.list_for_sensor(sensor.id, until=later(30))

    assert latest is not None and latest.value == 21.0
    assert [r.value for r in early] == [38.0]


def test_cycle_update_and_stages(uow: UowFactory, field: FieldIds) -> None:
    with uow() as u:
        cycle = u.cycles.get(field.cycle_id)
        u.cycles.update(replace(cycle, accumulated_gdd=412.5, status=CycleStatus.COMPLETED))
        stage = u.stages.add(Stage(field.cycle_id, "vegetative", started_at=T0, gdd_at_start=150))
        u.stages.update(replace(stage, ended_at=later(60)))
        u.commit()

    with uow() as u:
        cycle = u.cycles.get(field.cycle_id)
        stages = u.stages.list_by_cycle(field.cycle_id)

    assert cycle.accumulated_gdd == 412.5 and cycle.status is CycleStatus.COMPLETED
    assert stages[0].ended_at == later(60)


def test_task_json_params_and_money_round_trip(uow: UowFactory, field: FieldIds) -> None:
    task = replace(
        make_task(field, TaskStatus.PENDING_APPROVAL),
        params={"product": "urea", "n_kg_ha": 60},
        estimated_cost=Money(1_250_000, "COP"),
    )
    with uow() as u:
        stored = u.tasks.add(task, make_event(EventKind.PROPOSAL))
        u.commit()
    assert stored.id is not None

    with uow() as u:
        loaded = u.tasks.get(stored.id)
        pending = u.tasks.list(status=TaskStatus.PENDING_APPROVAL)

    assert loaded.params == {"product": "urea", "n_kg_ha": 60}
    assert loaded.estimated_cost == Money(1_250_000, "COP")
    assert [t.id for t in pending] == [stored.id]


def test_decision_round_trip(uow: UowFactory, field: FieldIds) -> None:
    with uow() as u:
        task = u.tasks.add(
            make_task(field, TaskStatus.PENDING_APPROVAL), make_event(EventKind.PROPOSAL)
        )
        assert task.id is not None
        u.decisions.add(
            Decision(
                task_id=task.id,
                requested_level=AutonomyLevel.AUTONOMOUS,
                effective_level=AutonomyLevel.APPROVAL,
                outcome=GateOutcome.AWAIT_APPROVAL,
                reason="Forecast rain 8 mm exceeds 5 mm limit.",
                created_at=T0,
                violations=({"rule": "irrigation.rain_forecast", "reason": "8 mm > 5 mm"},),
                inputs={"rain_forecast_mm_24h": 8.0},
            )
        )
        u.commit()

    with uow() as u:
        [decision] = u.decisions.list_by_task(task.id)

    assert decision.effective_level is AutonomyLevel.APPROVAL
    assert decision.violations[0]["rule"] == "irrigation.rain_forecast"


def test_notifications_unread_and_mark_read(uow: UowFactory) -> None:
    with uow() as u:
        note = u.notifications.add(Notification("Extra irrigation scheduled", created_at=T0))
        assert note.id is not None
        u.commit()

    with uow() as u:
        assert len(u.notifications.list(unread_only=True)) == 1
        u.notifications.mark_read(note.id, later(5))
        u.commit()

    with uow() as u:
        assert u.notifications.list(unread_only=True) == []


def test_report_round_trip(uow: UowFactory, field: FieldIds) -> None:
    with uow() as u:
        report = u.reports.add(Report(field.cycle_id, "es", "# Informe", created_at=T0))
        assert report.id is not None
        u.commit()

    with uow() as u:
        assert u.reports.get(report.id).content == "# Informe"
        assert len(u.reports.list_by_cycle(field.cycle_id)) == 1


def test_emergency_stop_defaults_off_and_logs_changes(uow: UowFactory) -> None:
    with uow() as u:
        assert u.control.get().emergency_stop_active is False
        u.control.set_emergency_stop(True, make_event(EventKind.EMERGENCY_STOP))
        u.commit()

    with uow() as u:
        state = u.control.get()
        events = u.events.list(kind=EventKind.EMERGENCY_STOP)

    assert state.emergency_stop_active is True
    assert state.changed_at == T0
    assert len(events) == 1


def test_emergency_stop_requires_its_event_kind(uow: UowFactory) -> None:
    with uow() as u, pytest.raises(ValueError, match="emergency_stop"):
        u.control.set_emergency_stop(True, make_event(EventKind.PROPOSAL))


def test_sim_clock_state_save_and_overwrite(uow: UowFactory) -> None:
    first = SimClockState(sim_anchor=T0, wall_anchor=T0, speed_factor=360.0, paused=False)
    with uow() as u:
        assert u.sim_clock.get() is None
        u.sim_clock.save(first)
        u.sim_clock.save(replace(first, paused=True))
        u.commit()

    with uow() as u:
        assert u.sim_clock.get() == replace(first, paused=True)


def test_datetimes_come_back_as_aware_utc(uow: UowFactory) -> None:
    local = datetime(2026, 10, 27, 1, 0, tzinfo=BOGOTA)
    with uow() as u:
        plot = u.plots.add(Plot("TZ", 0, 0, 1, created_at=local, utc_offset_hours=-5.0))
        assert plot.id is not None
        u.commit()

    with uow() as u:
        created_at = u.plots.get(plot.id).created_at

    assert created_at.tzinfo is UTC
    assert created_at == local
    assert created_at == datetime(2026, 10, 27, 6, 0, tzinfo=UTC)
    # Comparing with an aware deadline must work (revert window arithmetic).
    assert created_at < datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


def test_naive_datetime_is_rejected_on_write(uow: UowFactory) -> None:
    with uow() as u, pytest.raises(StatementError, match="naive"):
        u.plots.add(
            Plot("Naive", 0, 0, 1, created_at=datetime(2026, 10, 27, 6, 0), utc_offset_hours=0.0)
        )
