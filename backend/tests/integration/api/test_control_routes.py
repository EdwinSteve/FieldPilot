"""The simulated clock, the tick and the emergency stop over HTTP (D011, D022, D064, D065)."""

from fastapi.testclient import TestClient

from app.container import Container
from app.domain.models import Notification
from tests.integration.api.conftest import START, Farm


def test_the_clock_starts_where_it_was_stored(client: TestClient) -> None:
    clock = client.get("/clock").json()

    assert clock["now"] == START.isoformat().replace("+00:00", "Z")
    assert clock["paused"] is True


def test_resume_speed_pause_and_advance(client: TestClient) -> None:
    resumed = client.post("/clock", json={"action": "resume"}).json()
    sped = client.post("/clock", json={"action": "speed", "speed_factor": 360}).json()
    paused = client.post("/clock", json={"action": "pause"}).json()
    advanced = client.post("/clock", json={"action": "advance", "advance_seconds": 3600}).json()

    assert resumed["paused"] is False
    assert sped["speed_factor"] == 360
    assert paused["paused"] is True
    assert advanced["now"] > paused["now"]
    reasons = [e["reason"] for e in client.get("/events", params={"kind": "clock_changed"}).json()]
    assert len(reasons) == 4


def test_a_clock_change_without_its_value_is_422(client: TestClient) -> None:
    assert client.post("/clock", json={"action": "speed"}).status_code == 422
    assert client.post("/clock", json={"action": "advance"}).status_code == 422
    assert client.post("/clock", json={"action": "rewind"}).status_code == 422
    assert client.post("/clock", json={"action": "speed", "speed_factor": 0}).status_code == 422


def test_a_tick_records_readings_and_counts_nothing_twice(client: TestClient, farm: Farm) -> None:
    client.post("/clock", json={"action": "advance", "advance_seconds": 1800})

    first = client.post("/simulation/tick").json()
    second = client.post("/simulation/tick").json()

    assert first["readings_recorded"] == 1
    assert second["readings_recorded"] == 0
    assert first["zones_without_data"] == []


def test_the_emergency_stop_round_trip(client: TestClient) -> None:
    assert client.get("/emergency-stop").json()["active"] is False

    on = client.post("/emergency-stop", json={"active": True}).json()
    off = client.post("/emergency-stop", json={"active": False}).json()

    assert (on["active"], on["changed_by"]) == (True, "farmer:dashboard")
    assert off["active"] is False


def test_notifications_can_be_marked_read(client: TestClient, container: Container) -> None:
    with container.runtime.uow() as u:
        note = u.notifications.add(Notification("Aviso de prueba", START))
        u.commit()

    [unread] = client.get("/notifications", params={"unread_only": True}).json()
    read = client.post(f"/notifications/{note.id}/read").json()

    assert unread["message"] == "Aviso de prueba"
    assert read["read_at"] is not None
    assert client.get("/notifications", params={"unread_only": True}).json() == []
    assert client.post("/notifications/99/read").status_code == 404
