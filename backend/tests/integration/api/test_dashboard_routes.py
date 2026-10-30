"""What the dashboard reads beyond step 9: imagery, held reasons, scenarios (D014, D067)."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.container import Container
from app.domain.models import Plot
from tests.integration.api.actions import hold_for_rain, propose
from tests.integration.api.conftest import START, Farm, restart


def test_imagery_per_zone_with_low_vigour(client: TestClient, farm: Farm) -> None:
    body = client.get(f"/plots/{farm.plot_id}/imagery").json()

    assert body["scene"]["scene_id"] == "neiva-2026-10-28"
    assert body["scene"]["synthetic"] is True
    assert body["scene"]["segmentation_note"] is None
    assert body["zones"] == [
        {
            "zone_id": farm.zone_id,
            "ndvi_mean": 0.378,
            "low_ndvi_pct": 21.2,
            "bare_soil_pct": 25.3,  # the recorded SAM answer, replayed in mock mode
            "low_vigor": True,
        }
    ]


def test_a_plot_without_a_scene_has_none(client: TestClient, container: Container) -> None:
    with container.runtime.uow() as u:
        far = u.plots.add(Plot("Bogotá", 4.6, -74.1, 1.0, START, utc_offset_hours=-5.0))
        u.commit()

    assert client.get(f"/plots/{far.id}/imagery").json() == {"scene": None, "zones": []}
    assert client.get("/plots/99/imagery").status_code == 404


def test_a_held_task_says_why_in_spanish(
    client: TestClient, container: Container, farm: Farm
) -> None:
    hold_for_rain(container)
    held = propose(container, farm)
    container.clock_service.advance("test", timedelta(days=4))  # dry again
    allowed = propose(container, farm, volume_mm=12.0)

    tasks = {t["id"]: t for t in client.get("/tasks").json()}

    assert tasks[held]["reason_es"] == "Pendiente de aprobación por lluvia prevista (12 mm > 5 mm)"
    assert tasks[allowed]["reason_es"] is None


def _drought(start: datetime, hours: float = 48) -> dict[str, object]:
    return {
        "name": "drought",
        "start": start.isoformat(),
        "end": (start + timedelta(hours=hours)).isoformat(),
    }


def test_an_injected_drought_is_upcoming_then_active(
    client: TestClient, container: Container
) -> None:
    injected = client.post("/simulation/scenarios", json=_drought(START + timedelta(hours=1)))

    upcoming = client.get("/simulation/status").json()
    container.clock_service.advance("test", timedelta(hours=2))
    active = client.get("/simulation/status").json()

    assert injected.status_code == 200 and injected.json()["et0_multiplier"] == 2.0
    assert [s["name"] for s in upcoming["upcoming"]] == ["drought"] and upcoming["active"] == []
    assert [s["name"] for s in active["active"]] == ["drought"] and active["lost"] == []
    [event] = client.get("/events", params={"kind": "scenario_injected"}).json()
    assert event["actor"] == "farmer:dashboard"


def test_after_a_restart_the_drought_is_lost_not_shown_active(
    client: TestClient, database_url: str
) -> None:
    """D014: the UI never shows a scenario the simulator no longer applies."""
    client.post("/simulation/scenarios", json=_drought(START))

    with TestClient(restart(database_url)) as after:
        status = after.get("/simulation/status").json()

    assert status["active"] == [] and status["upcoming"] == []
    assert [s["name"] for s in status["lost"]] == ["drought"]


def test_an_ended_scenario_is_not_reported_lost(client: TestClient, database_url: str) -> None:
    client.post("/simulation/scenarios", json=_drought(START, hours=1))
    app = restart(database_url)
    app.state.container.clock_service.advance("test", timedelta(hours=2))

    with TestClient(app) as after:
        assert after.get("/simulation/status").json()["lost"] == []


def test_a_scenario_in_the_past_or_malformed_is_422(client: TestClient) -> None:
    past = client.post("/simulation/scenarios", json=_drought(START - timedelta(hours=1)))
    backwards = client.post(
        "/simulation/scenarios",
        json={"name": "drought", "start": START.isoformat(), "end": START.isoformat()},
    )
    unknown = client.post("/simulation/scenarios", json={**_drought(START), "name": "frost"})
    naive = client.post(
        "/simulation/scenarios",
        json={"name": "heavy_rain", "start": "2026-10-28T12:00:00", "end": "2026-10-28T13:00:00"},
    )

    assert past.status_code == 422 and past.json()["error"] == "ScenarioRejectedError"
    assert {r.status_code for r in (backwards, unknown, naive)} == {422}


def test_heavy_rain_takes_its_amount(client: TestClient) -> None:
    start = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
    body = {
        "name": "heavy_rain",
        "start": start.isoformat(),
        "end": (start + timedelta(hours=6)).isoformat(),
        "total_mm": 30,
    }

    assert client.post("/simulation/scenarios", json=body).json()["total_mm"] == 30.0


def test_an_approved_task_no_longer_shows_why_it_was_held(
    client: TestClient, container: Container, farm: Farm
) -> None:
    hold_for_rain(container)
    task_id = propose(container, farm)

    approved = client.post(f"/tasks/{task_id}/approve").json()

    assert approved["status"] == "executed"
    assert approved["reason_es"] is None
