"""A new plot in the demo gets simulated sensors, readings and imagery (D089)."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.domain.errors import ConfigError
from app.main import create_app
from app.services.sensor_kit import load_sensor_kit
from app.settings import Settings
from tests.conftest import CONFIG_DIR

TUNJA = {
    "name": "Finca nueva",
    "municipality": "Tunja",
    "department": "Boyacá",
    "latitude": 5.53,
    "longitude": -73.36,
    "area_ha": 1.5,
}


def _client(tmp_path: Path, profile: str) -> Iterator[TestClient]:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'demo.db'}",
        mock_llm=True,
        app_profile=profile,
        auth_required=profile != "demo",
        auth_jwt_secret="k" * 48,
        planner_site_builder="off",
    )
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture
def demo(tmp_path: Path) -> Iterator[TestClient]:
    yield from _client(tmp_path, "demo")


def _advance_and_tick(client: TestClient) -> Any:
    client.post("/clock", json={"action": "advance", "advance_seconds": 3600})
    return client.post("/simulation/tick").json()


def test_a_demo_plot_comes_with_two_zones_and_their_sensors(demo: TestClient) -> None:
    plot = demo.post("/plots", json=TUNJA).json()

    zones = demo.get(f"/plots/{plot['id']}/zones").json()

    assert [(z["name"], z["area_ha"], z["field_capacity_pct"]) for z in zones] == [
        ("Zone 1", 0.75, 32.0),
        ("Zone 2", 0.75, 32.0),
    ]
    sensors = demo.get(f"/readings?zone_id={zones[1]['id']}").json()
    assert [s["kind"] for s in sensors] == ["soil_moisture", "temperature", "humidity"]
    assert [r["value"] for r in sensors[0]["readings"]] == [18.0]  # the dry zone


def test_the_simulator_records_every_sensor_of_the_new_plot(demo: TestClient) -> None:
    plot = demo.post("/plots", json=TUNJA).json()
    zone = demo.get(f"/plots/{plot['id']}/zones").json()[0]

    tick = _advance_and_tick(demo)

    assert tick["zones_without_data"] == []
    assert tick["readings_recorded"] >= 6  # three sensors in each of the two zones
    sensors = demo.get(f"/readings?zone_id={zone['id']}").json()
    assert all(len(s["readings"]) >= 1 for s in sensors)
    assert len(sensors[0]["readings"]) == 2  # the kit's first reading, then the simulator's


def test_a_far_demo_plot_sees_the_synthetic_scene(demo: TestClient) -> None:
    plot = demo.post("/plots", json=TUNJA).json()
    sowing = {"crop": "maize", "sowing_date": "2026-10-01", "accept_own_risk": True}
    demo.post(f"/plots/{plot['id']}/cycles", json=sowing)

    imagery = demo.get(f"/plots/{plot['id']}/imagery").json()

    assert imagery["scene"]["synthetic"] is True
    assert len(imagery["zones"]) == 2


def test_outside_the_demo_a_new_plot_has_no_simulated_sensors(tmp_path: Path) -> None:
    for client in _client(tmp_path, "dev"):
        policy = client.get("/auth/privacy-policy").json()["version"]
        tokens = client.post("/auth/register", json={
            "phone": "3001234567", "full_name": "Ana", "password": "cafe-con-panela",
            "role": "farmer", "accept_privacy_policy": True, "privacy_policy_version": policy,
        }).json()["tokens"]  # fmt: skip
        farmer = {"Authorization": f"Bearer {tokens['access_token']}"}
        plot = client.post("/plots", json=TUNJA, headers=farmer).json()

        assert client.get(f"/plots/{plot['id']}/zones", headers=farmer).json() == []


def test_a_kit_whose_zones_do_not_cover_the_plot_is_refused(tmp_path: Path) -> None:
    shipped = (CONFIG_DIR / "demo_field.yaml").read_text(encoding="utf-8")
    broken = tmp_path / "demo_field.yaml"
    broken.write_text(shipped.replace("area_share: 0.5", "area_share: 0.4", 1), encoding="utf-8")
    with pytest.raises(ConfigError, match="add up to 1"):
        load_sensor_kit(broken)
    no_moisture = tmp_path / "no_moisture.yaml"
    no_moisture.write_text(shipped.replace("soil_moisture, ", ""), encoding="utf-8")
    with pytest.raises(ConfigError, match="soil_moisture"):
        load_sensor_kit(no_moisture)
