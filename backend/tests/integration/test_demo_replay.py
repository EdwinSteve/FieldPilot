"""The recorded two-day demo replays offline on a freshly seeded farm (D076).

Every step is the dashboard's own HTTP call, in the order docs/demo.md gives,
so this test fails if the seed, the recordings or the API drift apart.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.demo_seed import seed_demo_farm
from app.settings import Settings
from scripts.demo_script import DROUGHT, ONE_DAY, REJECT_REASON


def _demo(tmp_path: Path) -> tuple[TestClient, int]:
    url = f"sqlite:///{tmp_path / 'demo.db'}"
    plot_id = seed_demo_farm(url).plot_id
    settings = Settings(
        _env_file=None, database_url=url, mock_llm=True, app_profile="demo", auth_required=False
    )
    app = create_app(settings)
    return TestClient(app), plot_id


def _cycle(client: TestClient, plot_id: int) -> dict[str, Any]:
    response = client.post("/agent/daily-cycle", json={"plot_id": plot_id})
    assert response.status_code == 200, response.json()
    body: dict[str, Any] = response.json()
    assert body["status"] == "completed", body
    return body


def _tasks(client: TestClient) -> dict[str, dict[str, Any]]:
    return {f"{t['action_type']}:{t['status']}": t for t in client.get("/tasks").json()}


def test_the_two_day_demo_replays_offline(tmp_path: Path) -> None:
    client, plot_id = _demo(tmp_path)

    # Day 1, 2 Nov: 12 mm of rain coming; the gate holds the irrigation.
    _cycle(client, plot_id)
    [held] = client.get("/tasks", params={"status": "pending_approval"}).json()
    assert held["action_type"] == "irrigation"
    assert "lluvia prevista" in held["reason_es"]
    rejected = client.post(f"/tasks/{held['id']}/reject", json={"reason": REJECT_REASON})
    assert rejected.json()["status"] == "rejected"

    # Between days: "Inyectar sequía (48 h)", then "+1 día" (advance and tick).
    now = datetime.fromisoformat(client.get("/clock").json()["now"])
    drought = {"name": "drought", "start": now.isoformat(), "end": (now + DROUGHT).isoformat()}
    assert client.post("/simulation/scenarios", json=drought).status_code == 200
    advance = {"action": "advance", "advance_seconds": ONE_DAY.total_seconds()}
    assert client.post("/clock", json=advance).status_code == 200
    assert client.post("/simulation/tick").status_code == 200
    assert datetime.fromisoformat(client.get("/clock").json()["now"]) == datetime(
        2026, 11, 3, 11, 0, tzinfo=UTC
    )

    # Day 2, 3 Nov, dry: irrigated now, the rest scheduled with notice (D009).
    _cycle(client, plot_id)
    tasks = _tasks(client)
    assert "irrigation:executed" in tasks
    extra = tasks["extra_irrigation:scheduled"]
    assert extra["effective_level"] == "notify"
    assert extra["revert_open"] is True

    # The farmer reverts it inside the window; nothing is applied.
    reverted = client.post(f"/tasks/{extra['id']}/revert").json()
    assert reverted["task"]["status"] == "reverted" and reverted["applied_mm"] == 0.0
    assert client.get("/events", params={"task_id": extra["id"], "kind": "execution"}).json() == []

    reports = client.get("/reports").json()
    assert len(reports) == 2
    assert all("Zona 2" in report["content"] for report in reports)


def test_a_day_without_a_recording_answers_503(tmp_path: Path) -> None:
    client, plot_id = _demo(tmp_path)
    client.post(
        "/clock", json={"action": "advance", "advance_seconds": (5 * ONE_DAY).total_seconds()}
    )

    response = client.post("/agent/daily-cycle", json={"plot_id": plot_id})

    assert response.status_code == 503
    assert response.json()["error"] == "FixtureExhaustedError"
