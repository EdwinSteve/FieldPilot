"""Proposals made directly through the services, for the API tests."""

from datetime import UTC, datetime, timedelta

from app.container import Container
from app.domain.enums import ActionType
from app.domain.proposals import ProposedAction
from app.services.gate_context import local_day
from tests.integration.api.conftest import Farm


def propose(
    container: Container,
    farm: Farm,
    action: ActionType = ActionType.IRRIGATION,
    volume_mm: float = 15.0,
    hours_ahead: float = 0,
) -> int:
    with container.runtime.uow() as u:
        plot = u.plots.get(farm.plot_id)
    at = container.runtime.clock.now() + timedelta(hours=hours_ahead)
    result = container.proposals.propose(
        ProposedAction.create(
            action_type=action,
            plot_id=farm.plot_id,
            zone_id=farm.zone_id,
            scheduled_for=at,
            local_day=local_day(at, plot),
            params={"volume_mm": volume_mm},
            rationale="Prueba",
            proposed_by="test",
        )
    )
    assert result.task.id is not None
    return result.task.id


def hold_for_rain(container: Container) -> None:
    """Move the simulated clock to the morning of 2026-11-02, when the Open-Meteo fixture
    forecasts 12 mm: the gate holds every irrigation for approval."""
    rainy_morning = datetime(2026, 11, 2, 11, 0, tzinfo=UTC)
    container.clock_service.advance("test", rainy_morning - container.runtime.clock.now())
