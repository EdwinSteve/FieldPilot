"""Implements the agent's `FarmerOutbox`: reports and notifications, each with its event."""

from collections.abc import Callable

from app.autonomy.messages import MessageCatalog
from app.domain.enums import EventKind
from app.domain.models import Event, Notification, Report
from app.persistence.ports import UnitOfWork
from app.services.gate_context import active_cycle
from app.simulator.clock import Clock

UowFactory = Callable[[], UnitOfWork]
ACTOR = "system:agent"


class StoredOutbox:
    def __init__(self, uow: UowFactory, clock: Clock, messages: MessageCatalog) -> None:
        self._uow = uow
        self._clock = clock
        self._messages = messages

    def save_report(self, plot_id: int, text_es: str) -> int:
        """Store a report that passed its check (D052: nothing unverified gets here)."""
        with self._uow() as u:
            cycle = active_cycle(u, plot_id)
            if cycle.id is None:
                raise RuntimeError("active cycle without an id")
            report = u.reports.add(Report(cycle.id, "es", text_es, self._clock.now()))
            u.commit()
        if report.id is None:
            raise RuntimeError("database did not assign a report id")
        return report.id

    def notify(self, plot_id: int, text_key: str) -> None:
        """A catalogue text for the farmer, with its notification event, in one transaction."""
        now = self._clock.now()
        message = self._messages.agent_text(text_key)
        with self._uow() as u:
            u.notifications.add(Notification(message, now))
            u.events.append(
                Event(
                    kind=EventKind.NOTIFICATION,
                    actor=ACTOR,
                    reason=f"Farmer notified: {text_key} (plot {plot_id}).",
                    occurred_at=now,
                    inputs={"plot_id": plot_id, "text_key": text_key},
                )
            )
            u.commit()
