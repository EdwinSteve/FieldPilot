from fastapi.testclient import TestClient

from app.container import Container
from tests.integration.api.conftest import Farm


def test_plots_zones_and_readings(client: TestClient, farm: Farm) -> None:
    [plot] = client.get("/plots").json()
    [zone] = client.get(f"/plots/{farm.plot_id}/zones").json()
    [sensor] = client.get("/readings", params={"zone_id": farm.zone_id}).json()

    assert (plot["name"], plot["utc_offset_hours"]) == ("Neiva", -5.0)
    assert (zone["name"], zone["field_capacity_pct"]) == ("Zona 2", 32.0)
    assert sensor["kind"] == "soil_moisture"
    assert [r["value"] for r in sensor["readings"]] == [20.0]


def test_unknown_plot_or_zone_is_404(client: TestClient) -> None:
    plot = client.get("/plots/99/zones")
    zone = client.get("/readings", params={"zone_id": 99})

    assert (plot.status_code, zone.status_code) == (404, 404)
    assert plot.json() == {"error": "NotFoundError", "message": "Plot 99 not found"}


def test_cycles(client: TestClient, farm: Farm) -> None:
    [cycle] = client.get("/cycles").json()

    assert cycle["crop"] == "maize" and cycle["status"] == "active"
    assert client.get(f"/cycles/{farm.cycle_id}").json()["id"] == farm.cycle_id
    assert client.get("/cycles/99").status_code == 404


def test_events_filter_by_kind_and_task(
    client: TestClient, container: Container, farm: Farm
) -> None:
    client.post("/emergency-stop", json={"active": True})

    events = client.get("/events", params={"kind": "emergency_stop"}).json()

    assert [e["reason"] for e in events] == ["Emergency stop activated."]
    assert events[0]["actor"] == "farmer:dashboard"
    assert client.get("/events", params={"kind": "nonsense"}).status_code == 422


def test_reports_start_empty(client: TestClient, farm: Farm) -> None:
    assert client.get("/reports").json() == []


def test_a_crop_lists_its_stages_in_order(client: TestClient) -> None:
    """D077: the dashboard draws the stage bar from the catalogue, not from code."""
    body = client.get("/crops/maize").json()

    assert (body["name"], body["display_name"], body["display_es"]) == ("maize", "Maize", "Maíz")
    assert [s["name"] for s in body["stages"]] == [
        "sowing",
        "germination_emergence",
        "vegetative",
        "flowering",
        "grain_fill",
        "maturity_harvest",
    ]
    assert body["stages"][0] == {
        "name": "sowing",
        "display_name": "Sowing",
        "display_es": "Siembra",
        "gdd_start": 0.0,
    }
    assert body["maturity_gdd"] == 1472.2


def test_an_unknown_crop_is_404(client: TestClient) -> None:
    response = client.get("/crops/coffee")

    assert response.status_code == 404
    assert response.json() == {"error": "NotFoundError", "message": "Crop coffee not found"}
