from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime

from app.domain.enums import EventKind, TaskStatus
from app.domain.models import CropCycle, Plot
from app.persistence.unit_of_work import SqlUnitOfWork
from app.phenology.catalog import CropSpec
from app.services.agent_outbox import StoredOutbox
from app.services.field_reader import StoredFieldReader
from tests.conftest import T0, FieldIds, make_event, make_task
from tests.fakes import FakeClock
from tests.integration.services.world import MESSAGES

UowFactory = Callable[[], SqlUnitOfWork]


class NoRain:
    def rain_mm_next_24h(self, plot_id: int, at: datetime) -> float | None:
        return 0.0


def test_a_saved_report_belongs_to_the_active_cycle(uow: UowFactory, field: FieldIds) -> None:
    report_id = StoredOutbox(uow, FakeClock(T0), MESSAGES).save_report(field.plot_id, "Informe.")

    with uow() as u:
        report = u.reports.get(report_id)
    assert (report.cycle_id, report.language, report.content) == (field.cycle_id, "es", "Informe.")
    assert report.created_at == T0


def test_a_notification_is_written_with_its_event(uow: UowFactory, field: FieldIds) -> None:
    StoredOutbox(uow, FakeClock(T0), MESSAGES).notify(field.plot_id, "report.escalated_unverified")

    with uow() as u:
        [note] = u.notifications.list(unread_only=True)
        [event] = u.events.list(kind=EventKind.NOTIFICATION)
    assert note.message == MESSAGES.agent_text("report.escalated_unverified")
    assert event.actor == "system:agent"
    assert event.inputs == {"plot_id": field.plot_id, "text_key": "report.escalated_unverified"}


def test_task_status_is_read_from_the_plot_cycle(
    uow: UowFactory, field: FieldIds, maize: CropSpec
) -> None:
    with uow() as u:
        task = u.tasks.add(
            make_task(field, TaskStatus.PENDING_APPROVAL), make_event(EventKind.PROPOSAL)
        )
        u.commit()
    assert task.id is not None
    reader = StoredFieldReader(uow, NoRain(), {"maize": maize}, FakeClock(T0))

    assert reader.task_status(field.plot_id, task.id) == "pending_approval"
    assert reader.task_status(field.plot_id, task.id + 100) is None


def test_a_task_of_another_plot_has_no_status_here(
    uow: UowFactory, field: FieldIds, maize: CropSpec
) -> None:
    with uow() as u:
        other = u.plots.add(Plot("Other", 4.6, -74.1, 1.0, created_at=T0, utc_offset_hours=-5.0))
        assert other.id is not None
        cycle = u.cycles.add(CropCycle(other.id, "maize", date(2026, 10, 1)))
        assert cycle.id is not None
        task = u.tasks.add(
            replace(make_task(field), cycle_id=cycle.id), make_event(EventKind.PROPOSAL)
        )
        u.commit()
    assert task.id is not None
    reader = StoredFieldReader(uow, NoRain(), {"maize": maize}, FakeClock(T0))

    assert reader.task_status(other.id, task.id) == "scheduled"
    assert reader.task_status(field.plot_id, task.id) is None
