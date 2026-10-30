"""The seeded farm is exactly what the mock demo day replays on (D074)."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.demo_seed import seed_demo_farm
from app.settings import Settings


def test_the_mock_day_completes_on_a_seeded_farm(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'seed.db'}"
    summary = seed_demo_farm(url)

    assert (summary.plot_id, summary.zone_id) == (1, 1)

    client = TestClient(create_app(Settings(_env_file=None, database_url=url, mock_llm=True)))
    cycle = client.post("/agent/daily-cycle", json={"plot_id": summary.plot_id}).json()

    assert cycle["status"] == "completed"
    tasks = {t["action_type"]: t for t in client.get("/tasks").json()}
    assert tasks["irrigation"]["status"] == "executed"
    assert tasks["irrigation"]["params"]["volume_mm"] == 15.0
    assert tasks["extra_irrigation"]["status"] == "scheduled"
    assert len(client.get("/reports").json()) == 1
