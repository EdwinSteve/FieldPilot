"""Approve, reject and revert through HTTP, with the real gate (D008, D011, D062)."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.container import Container
from app.domain.enums import ActionType
from app.domain.proposals import ProposedAction
from app.services.gate_context import local_day
from tests.integration.api.conftest import Farm


def _propose(
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


def _hold_for_rain(container: Container) -> None:
    """Move the simulated clock to the morning of 2026-11-02, when the Open-Meteo fixture
    forecasts 12 mm: the gate holds every irrigation for approval."""
    rainy_morning = datetime(2026, 11, 2, 11, 0, tzinfo=UTC)
    container.clock_service.advance("test", rainy_morning - container.runtime.clock.now())


def test_a_held_task_is_listed_and_approved(
    client: TestClient, container: Container, farm: Farm
) -> None:
    _hold_for_rain(container)
    task_id = _propose(container, farm)

    [pending] = client.get("/tasks", params={"status": "pending_approval"}).json()
    approved = client.post(f"/tasks/{task_id}/approve")

    assert pending["id"] == task_id and pending["effective_level"] == "approval"
    assert approved.status_code == 200
    assert approved.json()["status"] == "executed"


def test_approving_twice_is_a_conflict(
    client: TestClient, container: Container, farm: Farm
) -> None:
    _hold_for_rain(container)
    task_id = _propose(container, farm)
    client.post(f"/tasks/{task_id}/approve")

    again = client.post(f"/tasks/{task_id}/approve")

    assert again.status_code == 409
    assert again.json()["error"] == "InvalidTransitionError"


def test_a_rejection_keeps_its_reason(client: TestClient, container: Container, farm: Farm) -> None:
    _hold_for_rain(container)
    task_id = _propose(container, farm)

    response = client.post(f"/tasks/{task_id}/reject", json={"reason": "Esperaré la lluvia"})
    [rejection] = client.get("/events", params={"task_id": task_id, "kind": "rejection"}).json()

    assert response.json()["status"] == "rejected"
    assert rejection["reason"] == "Rejected by the farmer: Esperaré la lluvia"


def test_a_notify_task_carries_its_revert_window(
    client: TestClient, container: Container, farm: Farm
) -> None:
    """D011: the backend sends revert_deadline and revert_open; the UI decides nothing."""
    task_id = _propose(container, farm, ActionType.EXTRA_IRRIGATION, 10.0, hours_ahead=24)

    [task] = [t for t in client.get("/tasks").json() if t["id"] == task_id]

    assert task["status"] == "scheduled"
    assert task["revert_open"] is True
    assert task["revert_deadline"] is not None
    assert 0 < task["revert_remaining_seconds"] <= 6 * 3600


def test_revert_then_revert_again(client: TestClient, container: Container, farm: Farm) -> None:
    task_id = _propose(container, farm, ActionType.EXTRA_IRRIGATION, 10.0, hours_ahead=24)

    first = client.post(f"/tasks/{task_id}/revert")
    second = client.post(f"/tasks/{task_id}/revert")

    assert first.status_code == 200
    assert first.json()["task"]["status"] == "reverted"
    assert first.json()["task"]["revert_open"] is False
    assert first.json()["applied_mm"] == 0.0
    assert second.status_code == 409 and second.json()["error"] == "RevertRefusedError"


def test_an_autonomous_task_has_no_revert_window(
    client: TestClient, container: Container, farm: Farm
) -> None:
    task_id = _propose(container, farm)

    [task] = [t for t in client.get("/tasks").json() if t["id"] == task_id]

    assert (task["revert_open"], task["revert_deadline"]) == (None, None)


def test_an_unknown_task_is_404(client: TestClient) -> None:
    assert client.post("/tasks/99/approve").status_code == 404
    assert client.post("/tasks/99/revert").status_code == 404
