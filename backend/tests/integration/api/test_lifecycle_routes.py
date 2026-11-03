"""From plan to passport (D083): plots, their site data, the sowing and the harvest."""

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fieldpilot_planner.serving import SiteSnapshot
from sqlalchemy import text

from app.container import Container
from app.domain.enums import ActionType, AutonomyLevel, EventKind, SensorKind, TaskStatus
from app.domain.errors import MissingDataError
from app.domain.models import Event, Reading, Sensor, Task
from app.persistence.unit_of_work import SqlUnitOfWork
from app.planning.site_jobs import SiteBuildError, SiteJobs
from app.planning.sites import FileSiteSource
from app.services.gate_context import active_cycle
from app.services.plots import PlotService
from app.settings import REPO_ROOT
from app.simulator.clock import system_wall_clock
from tests.integration.api.conftest import Farm

Runner = Callable[[Callable[[], None]], None]
DEMO_SITE = REPO_ROOT / "data" / "fixtures" / "planner" / "site_1.json"
TODAY = date(2026, 10, 28)  # the paused clock of the API tests, in Neiva
LA_PLATA = {
    "name": "Finca La Esperanza", "municipality": "La Plata", "department": "Huila",
    "latitude": 2.39, "longitude": -75.89, "area_ha": 3.5,
}  # fmt: skip


class CopyingBuilder:
    """Writes the demo snapshot at the plot's coordinates: no network in tests."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def build(self, lat: float, lon: float, out: Path) -> None:
        if self.fail:
            raise SiteBuildError("Sin conexión con NASA POWER.")
        snapshot = SiteSnapshot.from_json(DEMO_SITE.read_text(encoding="utf-8"))
        out.write_text(replace(snapshot, lat=lat, lon=lon).to_json(), encoding="utf-8")


@pytest.fixture
def app_overrides(tmp_path: Path) -> dict[str, Any]:
    """Built snapshots go to a temporary directory, never into data/."""
    return {"planner_sites_dir": tmp_path / "sites"}


def _with_builder(
    app: FastAPI, tmp_path: Path, builder: CopyingBuilder, runner: Runner | None = None
) -> None:
    """Swap in site jobs that run at once (or queue), with a builder that needs no network."""
    container: Container = app.state.container
    sites_dir = tmp_path / "sites"
    jobs = SiteJobs(container.runtime.uow, system_wall_clock, builder, sites_dir,
                    runner or (lambda task: task()))  # fmt: skip
    sites = FileSiteSource([DEMO_SITE.parent, sites_dir])  # the same places the planner reads
    plots = PlotService(container.runtime.uow, container.runtime.clock, sites, jobs)
    app.state.container = replace(container, plots=plots)


def _raw_sql(container: Container, statement: str, params: dict[str, Any] | None = None) -> None:
    """Someone editing the database behind the API's back."""
    with container.runtime.uow() as uow:
        assert isinstance(uow, SqlUnitOfWork)
        uow._session.execute(text(statement), params or {})  # noqa: SLF001
        uow.commit()


def _week(client: TestClient, plot_id: int, day: date) -> list[dict[str, Any]]:
    plan = client.get(
        f"/plots/{plot_id}/planting-plan", params={"from": day.isoformat(), "weeks": 1}
    )
    assert plan.status_code == 200, plan.json()
    outlooks: list[dict[str, Any]] = plan.json()["weeks"][0]["outlooks"]
    return outlooks


def _sow(client: TestClient, plot_id: int, crop: str, day: date, risk: bool = False) -> Any:
    body = {"crop": crop, "sowing_date": day.isoformat(), "accept_own_risk": risk}
    return client.post(f"/plots/{plot_id}/cycles", json=body)


def _harvest(client: TestClient, cycle_id: int, day: date, kg: float = 1200.0) -> Any:
    body = {"harvested_on": day.isoformat(), "quantity_kg": kg, "grade": "first"}
    return client.post(f"/cycles/{cycle_id}/harvest", json=body)


# --- plots and their site data ---------------------------------------------------------


def test_a_new_plot_builds_its_site_data_and_then_gets_a_plan(
    app: FastAPI, client: TestClient, tmp_path: Path
) -> None:
    _with_builder(app, tmp_path, CopyingBuilder())

    created = client.post("/plots", json=LA_PLATA)

    assert created.status_code == 201, created.json()
    plot = created.json()
    assert (plot["municipality"], plot["utc_offset_hours"]) == ("La Plata", -5.0)
    site = client.get(f"/plots/{plot['id']}/site").json()
    assert site["status"] == "ready"
    assert site["weather_until"] is not None
    assert len(_week(client, plot["id"], TODAY)) == 8


def test_a_failed_build_says_why_and_can_be_retried(
    app: FastAPI, client: TestClient, tmp_path: Path
) -> None:
    builder = CopyingBuilder(fail=True)
    _with_builder(app, tmp_path, builder)
    plot_id = client.post("/plots", json=LA_PLATA).json()["id"]

    failed = client.get(f"/plots/{plot_id}/site").json()
    assert (failed["status"], failed["message"]) == ("failed", "Sin conexión con NASA POWER.")
    plan = client.get(f"/plots/{plot_id}/planting-plan")
    assert plan.status_code == 409

    builder.fail = False
    retried = client.post(f"/plots/{plot_id}/site")
    assert (retried.status_code, retried.json()["status"]) == (202, "ready")


def test_a_pending_build_is_not_started_twice(
    app: FastAPI, client: TestClient, tmp_path: Path
) -> None:
    queued: list[Callable[[], None]] = []
    _with_builder(app, tmp_path, CopyingBuilder(), queued.append)
    plot_id = client.post("/plots", json=LA_PLATA).json()["id"]

    assert client.get(f"/plots/{plot_id}/site").json()["status"] == "pending"
    assert client.post(f"/plots/{plot_id}/site").status_code == 409


@pytest.mark.parametrize(
    "change",
    [{"latitude": 40.4}, {"longitude": -3.7}, {"area_ha": 0}, {"area_ha": 5000}, {"name": "x"}],
)
def test_a_plot_outside_colombia_or_out_of_bounds_is_refused(
    client: TestClient, change: dict[str, Any]
) -> None:
    assert client.post("/plots", json=LA_PLATA | change).status_code == 422


def test_a_snapshot_never_serves_a_plot_at_other_coordinates(
    client: TestClient, container: Container, farm: Farm
) -> None:
    """site_1.json is Neiva's: a plot 1 elsewhere must not borrow it."""
    _raw_sql(container, "UPDATE plot SET latitude = 6.25 WHERE id = :id", {"id": farm.plot_id})
    assert client.get(f"/plots/{farm.plot_id}/site").json()["status"] == "missing"


# --- the sowing confirmation -------------------------------------------------------------


def test_one_active_cycle_per_plot(client: TestClient, farm: Farm) -> None:
    response = _sow(client, farm.plot_id, "maize", TODAY)
    assert (response.status_code, response.json()["error"]) == (409, "ActiveCycleExistsError")


@pytest.mark.parametrize(
    ("crop", "day"),
    [("maize", TODAY + timedelta(days=1)), ("maize", TODAY - timedelta(days=61)),
     ("Maíz", TODAY), ("x", TODAY)],
)  # fmt: skip
def test_a_sowing_is_confirmed_only_after_it_happened(
    client: TestClient, farm: Farm, crop: str, day: date
) -> None:
    _harvest(client, farm.cycle_id, TODAY)
    assert _sow(client, farm.plot_id, crop, day).status_code == 422


def test_a_recommended_crop_follows_the_plan(client: TestClient, farm: Farm) -> None:
    _harvest(client, farm.cycle_id, TODAY - timedelta(days=1))
    best = _week(client, farm.plot_id, TODAY)[0]

    response = _sow(client, farm.plot_id, best["crop"], TODAY)

    assert response.status_code == 201, response.json()
    cycle = response.json()
    assert (cycle["own_risk"], cycle["plan"]["rank"]) == (False, 1)
    assert cycle["plan"]["rel_yield_p50"] == best["rel_yield_p50"]
    assert cycle["automated"] is (best["crop"] == "maize")


def test_a_crop_outside_the_top_three_needs_the_farmers_own_risk(
    client: TestClient, farm: Farm, container: Container
) -> None:
    _harvest(client, farm.cycle_id, TODAY - timedelta(days=1))
    week = _week(client, farm.plot_id, TODAY)
    worst = week[-1]

    refused = _sow(client, farm.plot_id, worst["crop"], TODAY)
    assert (refused.status_code, refused.json()["error"]) == (422, "OwnRiskRequiredError")
    assert week[0]["name_es"] in refused.json()["message"]

    accepted = _sow(client, farm.plot_id, worst["crop"], TODAY, risk=True)
    assert accepted.status_code == 201
    assert (accepted.json()["own_risk"], accepted.json()["plan"]["rank"]) == (True, len(week))
    with container.runtime.uow() as uow:
        started = uow.events.list(kind=EventKind.CYCLE_STARTED)
    assert started[-1].inputs["own_risk"] is True


def test_any_crop_may_be_sown_at_own_risk_as_a_manual_cycle(
    client: TestClient, farm: Farm, container: Container
) -> None:
    _harvest(client, farm.cycle_id, TODAY - timedelta(days=1))
    assert _sow(client, farm.plot_id, "aguacate_hass", TODAY).status_code == 422

    cycle = _sow(client, farm.plot_id, "aguacate_hass", TODAY, risk=True).json()

    assert (cycle["automated"], cycle["plan"], cycle["own_risk"]) == (False, None, True)


def test_stage_two_never_acts_on_a_manual_cycle(
    client: TestClient, farm: Farm, container: Container
) -> None:
    _harvest(client, farm.cycle_id, TODAY - timedelta(days=1))
    cycle = _sow(client, farm.plot_id, "aguacate_hass", TODAY, risk=True).json()
    _temperatures(container, farm, TODAY, days=3)  # what degree-days would need

    client.post("/clock", json={"action": "advance", "advance_seconds": 3 * 86400})
    assert client.post("/simulation/tick").status_code == 200

    with container.runtime.uow() as uow:
        assert uow.cycles.get(cycle["id"]).gdd_updated_through is None
        with pytest.raises(MissingDataError, match="no active automated crop cycle"):
            active_cycle(uow, farm.plot_id)


def _temperatures(container: Container, farm: Farm, first: date, days: int) -> None:
    with container.runtime.uow() as uow:
        sensor = uow.sensors.add(Sensor(farm.zone_id, SensorKind.TEMPERATURE, "°C"))
        assert sensor.id is not None
        readings = [
            Reading(sensor.id, value, datetime.combine(first + timedelta(days=d), time(h), UTC))
            for d in range(days)
            for h, value in ((11, 21.0), (20, 32.0))
        ]
        uow.readings.add_many(readings)
        uow.commit()


# --- the harvest confirmation and the passport -------------------------------------------


def test_the_harvest_creates_one_lot_with_a_verified_passport(
    client: TestClient, farm: Farm, container: Container
) -> None:
    response = _harvest(client, farm.cycle_id, TODAY, kg=5200.5)

    assert response.status_code == 201, response.json()
    lot = response.json()
    assert lot["code"] == f"FP-{farm.plot_id}-20261028-1"
    assert lot["passport_path"] == f"/trace/{lot['code']}"
    cycle = client.get(f"/cycles/{farm.cycle_id}").json()
    assert (cycle["status"], cycle["lot_code"]) == ("completed", lot["code"])

    passport = client.get(lot["passport_path"]).json()
    assert passport["quantity_kg"] == 5200.5
    assert passport["integrity"]["verified"] is True
    assert passport["cultivation"]["data_source"] == "measured"
    assert passport["plan"]["known"] is False  # the seed predates the sowing confirmation
    assert "2.93" not in str(passport) and "75.28" not in str(passport)
    with container.runtime.uow() as uow:
        kinds = [e.kind for e in uow.events.list()]
    assert EventKind.HARVEST_CONFIRMED in kinds and EventKind.LOT_COMMISSIONED in kinds


@pytest.mark.parametrize(
    ("day", "kg"),
    [(date(2026, 10, 1), 100.0), (TODAY + timedelta(days=1), 100.0), (TODAY, 0.0),
     (TODAY, 100_000 * 2.0 + 1)],
)  # fmt: skip
def test_a_harvest_that_cannot_be_true_is_refused(
    client: TestClient, farm: Farm, day: date, kg: float
) -> None:
    assert _harvest(client, farm.cycle_id, day, kg).status_code == 422
    assert client.get(f"/cycles/{farm.cycle_id}").json()["status"] == "active"


def test_a_cycle_is_harvested_once(client: TestClient, farm: Farm) -> None:
    assert _harvest(client, farm.cycle_id, TODAY).status_code == 201
    again = _harvest(client, farm.cycle_id, TODAY)
    assert (again.status_code, again.json()["error"]) == (409, "InvalidTransitionError")


def _task(container: Container, farm: Farm, executed: bool) -> None:
    """An irrigation of 12 mm, left waiting for approval or carried through to executed."""
    now = container.runtime.clock.now()
    status = TaskStatus.SCHEDULED if executed else TaskStatus.PENDING_APPROVAL
    task = Task(
        farm.cycle_id, ActionType.IRRIGATION, now, status, AutonomyLevel.APPROVAL,
        "Riego de prueba.", now, now, zone_id=farm.zone_id, params={"volume_mm": 12},
    )  # fmt: skip
    with container.runtime.uow() as uow:
        stored = uow.tasks.add(task, Event(EventKind.PROPOSAL, "agent:irrigation", "Riego.", now))
        if executed and stored.id is not None:
            done = Event(EventKind.EXECUTION, "system", "Riego aplicado.", now, task_id=stored.id)
            uow.tasks.transition(stored.id, TaskStatus.EXECUTED, done)
        uow.commit()


def test_a_field_with_open_tasks_is_not_harvested(
    client: TestClient, farm: Farm, container: Container
) -> None:
    _task(container, farm, executed=False)
    response = _harvest(client, farm.cycle_id, TODAY)
    assert (response.status_code, response.json()["error"]) == (409, "OpenTasksError")


def test_an_edited_event_log_breaks_the_passport(
    client: TestClient, farm: Farm, container: Container
) -> None:
    _task(container, farm, executed=True)
    lot = _harvest(client, farm.cycle_id, TODAY).json()
    passport = client.get(lot["passport_path"]).json()
    assert passport["integrity"]["verified"] is True
    assert passport["cultivation"]["irrigation_mm_total"] == 12.0

    _raw_sql(container, "UPDATE event SET reason = 'editado' WHERE kind = 'proposal'")

    assert client.get(lot["passport_path"]).json()["integrity"]["verified"] is False


def test_an_unknown_lot_is_a_404(client: TestClient) -> None:
    assert client.get("/trace/FP-9-20260101-1").status_code == 404
