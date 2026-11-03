"""GET /plots/{id}/planting-plan: the trained planner served on the demo plot (D079, D081)."""

from typing import Any

from fastapi.testclient import TestClient

from app.container import Container
from app.domain.enums import EventKind
from app.domain.models import Plot
from tests.integration.api.conftest import Farm


def _plan(client: TestClient, plot_id: int, **query: Any) -> Any:
    return client.get(f"/plots/{plot_id}/planting-plan", params=query)


def test_the_plan_ranks_every_crop_for_each_sowing_week(client: TestClient, farm: Farm) -> None:
    response = _plan(client, farm.plot_id, **{"from": "2026-11-02", "weeks": 3})

    assert response.status_code == 200, response.json()
    plan = response.json()
    assert plan["model"].startswith("planner-")  # the adopted network, not B0
    assert [w["sowing_date"] for w in plan["weeks"]] == ["2026-11-02", "2026-11-09", "2026-11-16"]
    for week in plan["weeks"]:
        p50 = [o["rel_yield_p50"] for o in week["outlooks"]]
        assert p50 == sorted(p50, reverse=True)
        assert len(p50) == 8
        for o in week["outlooks"]:
            assert 0 <= o["rel_yield_p10"] <= o["rel_yield_p50"] <= o["rel_yield_p90"] <= 1
            assert 0 <= o["p_success"] <= 1
    automatable = {o["crop"] for o in plan["weeks"][0]["outlooks"] if o["automatable"]}
    assert automatable == {"maize"}  # the only crop with a YAML in config/crops/


def test_each_plan_served_is_logged_with_its_data(
    client: TestClient, farm: Farm, container: Container
) -> None:
    _plan(client, farm.plot_id, weeks=2)

    with container.runtime.uow() as uow:
        events = uow.events.list(kind=EventKind.PLANTING_PLAN_SERVED)
    assert len(events) == 1
    inputs = events[0].inputs
    assert events[0].actor == "farmer:dashboard"
    assert inputs["weeks"] == 2
    assert isinstance(inputs["site_sha256"], str) and len(inputs["site_sha256"]) == 64


def test_the_plan_never_creates_a_task(client: TestClient, farm: Farm) -> None:
    before = client.get("/tasks").json()
    _plan(client, farm.plot_id)
    assert client.get("/tasks").json() == before


def test_a_plot_without_site_data_is_a_conflict(
    client: TestClient, farm: Farm, container: Container
) -> None:
    with container.runtime.uow() as uow:
        now = container.runtime.clock.now()
        other = uow.plots.add(Plot("Sin datos", 4.6, -74.1, 1.0, now, utc_offset_hours=-5.0))
        uow.commit()
    assert other.id is not None

    response = _plan(client, other.id)

    assert response.status_code == 409
    assert "make planner-site" in response.json()["message"]


def test_weeks_stay_within_one_to_twelve(client: TestClient, farm: Farm) -> None:
    assert _plan(client, farm.plot_id, weeks=0).status_code == 422
    assert _plan(client, farm.plot_id, weeks=13).status_code == 422
