"""D016 required tests (step 11): explicit clock advances drive the revert window and
the moment a scheduled task runs. Through HTTP, as the dashboard and the demo do."""

from fastapi.testclient import TestClient

from app.container import Container
from app.domain.enums import ActionType
from tests.integration.api.actions import propose
from tests.integration.api.conftest import Farm

HOUR = 3_600
WINDOW = 6 * HOUR  # revert_window_seconds in autonomy.yaml


def _advance(client: TestClient, seconds: float) -> None:
    """Move the simulated clock and let the simulation catch up, as "+1 h" does."""
    assert (
        client.post("/clock", json={"action": "advance", "advance_seconds": seconds}).status_code
        == 200
    )
    assert client.post("/simulation/tick").status_code == 200


def _extra_irrigation(container: Container, farm: Farm) -> int:
    """A NOTIFY task for tomorrow: scheduled, with a 6 h revert window (D009)."""
    return propose(container, farm, ActionType.EXTRA_IRRIGATION, 10.0, hours_ahead=24)


def _task(client: TestClient, task_id: int) -> dict[str, object]:
    [task] = [t for t in client.get("/tasks").json() if t["id"] == task_id]
    return task


def test_a_revert_inside_the_window_succeeds(
    client: TestClient, container: Container, farm: Farm
) -> None:
    task_id = _extra_irrigation(container, farm)
    _advance(client, WINDOW - HOUR)

    assert _task(client, task_id)["revert_open"] is True
    response = client.post(f"/tasks/{task_id}/revert")

    assert response.status_code == 200
    assert response.json()["task"]["status"] == "reverted"
    assert response.json()["applied_mm"] == 0.0


def test_a_revert_past_the_window_is_409(
    client: TestClient, container: Container, farm: Farm
) -> None:
    task_id = _extra_irrigation(container, farm)
    _advance(client, WINDOW + 1)

    assert _task(client, task_id)["revert_open"] is False
    response = client.post(f"/tasks/{task_id}/revert")

    assert response.status_code == 409
    assert response.json()["error"] == "RevertRefusedError"
    assert _task(client, task_id)["status"] == "scheduled"  # refused, nothing changed


def test_a_scheduled_task_runs_only_once_an_advance_crosses_its_time(
    client: TestClient, container: Container, farm: Farm
) -> None:
    task_id = _extra_irrigation(container, farm)

    _advance(client, 23 * HOUR)
    before = client.get("/events", params={"task_id": task_id, "kind": "execution"}).json()
    still = _task(client, task_id)["status"]
    _advance(client, 1 * HOUR)
    after = client.get("/events", params={"task_id": task_id, "kind": "execution"}).json()

    assert (still, before) == ("scheduled", [])
    assert _task(client, task_id)["status"] == "executed"
    assert len(after) == 1


def test_every_advance_is_logged(client: TestClient, farm: Farm) -> None:
    _advance(client, HOUR)
    _advance(client, 2 * HOUR)

    reasons = [e["reason"] for e in client.get("/events", params={"kind": "clock_changed"}).json()]
    assert reasons == ["Simulated clock: advance 1:00:00.", "Simulated clock: advance 2:00:00."]
