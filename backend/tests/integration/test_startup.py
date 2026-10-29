"""create_app() must refuse to start on an unsafe configuration (D005, D006, D025)."""

import shutil
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.domain.enums import ActionType, EventKind, TaskStatus
from app.domain.errors import ConfigError
from app.domain.models import CropCycle, Plot, Zone
from app.main import create_app
from app.persistence.db import create_db_engine, init_schema
from app.persistence.unit_of_work import SqlUnitOfWork
from app.settings import Settings
from tests.builders import BRIEF_ALWAYS_APPROVAL
from tests.conftest import CONFIG_DIR, T0, FieldIds, make_event, make_task


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """A writable copy of the shipped configuration."""
    target = tmp_path / "config"
    shutil.copytree(CONFIG_DIR, target)
    return target


def edit_yaml(path: Path, change: Callable[[dict[str, Any]], None]) -> None:
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(raw)
    path.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")


def start(config_dir: Path) -> None:
    create_app(Settings(_env_file=None, config_dir=config_dir, database_url="sqlite://"))


def test_shipped_configuration_starts(config_dir: Path) -> None:
    app = create_app(Settings(_env_file=None, config_dir=config_dir, database_url="sqlite://"))

    assert app.state.config.policy.revert_window_seconds == 21600
    assert app.state.config.limits.max_moisture_pct_fc == 85


@pytest.mark.parametrize("action_type", BRIEF_ALWAYS_APPROVAL)
def test_refuses_to_start_when_a_mandatory_type_is_below_approval(
    config_dir: Path, action_type: ActionType
) -> None:
    edit_yaml(
        config_dir / "autonomy.yaml",
        lambda raw: raw["defaults"].update({str(action_type): "notify"}),
    )

    with pytest.raises(ConfigError, match=f"{action_type} must be approval"):
        start(config_dir)


@pytest.mark.parametrize("action_type", BRIEF_ALWAYS_APPROVAL)
def test_refuses_to_start_when_a_mandatory_type_is_dropped_from_the_list(
    config_dir: Path, action_type: ActionType
) -> None:
    edit_yaml(
        config_dir / "autonomy.yaml",
        lambda raw: raw["always_approval"].remove(str(action_type)),
    )

    with pytest.raises(ConfigError, match=f"always_approval must include: {action_type}"):
        start(config_dir)


def test_refuses_to_start_when_a_stage_override_relaxes_a_level(config_dir: Path) -> None:
    def relax(raw: dict[str, Any]) -> None:
        raw["stages"][0]["autonomy"] = {"extra_irrigation": "autonomous"}

    edit_yaml(config_dir / "crops" / "maize.yaml", relax)

    with pytest.raises(ConfigError, match="relaxes default"):
        start(config_dir)


def test_refuses_to_start_with_an_incomplete_safety_file(config_dir: Path) -> None:
    edit_yaml(config_dir / "safety.yaml", lambda raw: raw.pop("max_calendar_shift_days"))

    with pytest.raises(ConfigError, match="max_calendar_shift_days"):
        start(config_dir)


def test_refuses_to_start_when_a_message_is_missing(config_dir: Path) -> None:
    edit_yaml(config_dir / "messages" / "es.yaml", lambda raw: raw["rules"].pop("missing_input"))

    with pytest.raises(ConfigError, match="missing_input"):
        start(config_dir)


def test_crop_catalog_uses_the_moisture_limit_from_safety_yaml(config_dir: Path) -> None:
    # maize targets up to 80 % FC; a 75 % safety ceiling must reject it at startup.
    edit_yaml(config_dir / "safety.yaml", lambda raw: raw.update({"max_moisture_pct_fc": 75}))

    with pytest.raises(ConfigError, match="safety limit"):
        start(config_dir)


def test_refuses_to_start_without_actuation_config(config_dir: Path) -> None:
    (config_dir / "actuation.yaml").unlink()

    with pytest.raises(ConfigError, match=r"actuation\.yaml"):
        start(config_dir)


def test_shipped_configuration_loads_the_irrigation_rate(config_dir: Path) -> None:
    app = create_app(Settings(_env_file=None, config_dir=config_dir, database_url="sqlite://"))

    assert app.state.config.actuation.irrigation_rate_mm_per_h == 6.0


# --- startup reconciliation (D013, D014) -----------------------------------


def seed_interrupted_request(database_url: str) -> int:
    """A task whose execution was requested and never closed, as after a crash."""

    engine = create_db_engine(database_url)
    init_schema(engine)
    with SqlUnitOfWork(engine) as u:
        plot = u.plots.add(Plot("Demo", 2.9, -75.3, 2.0, T0, utc_offset_hours=-5.0))
        assert plot.id is not None
        zone = u.zones.add(Zone(plot.id, "Zona 2", 0.5, 32.0, valve_id="v2"))
        cycle = u.cycles.add(CropCycle(plot.id, "maize", date(2026, 10, 1)))
        assert zone.id is not None and cycle.id is not None
        ids = FieldIds(plot.id, zone.id, cycle.id)
        task = u.tasks.add(make_task(ids, TaskStatus.SCHEDULED), make_event(EventKind.PROPOSAL))
        assert task.id is not None
        u.events.append(
            make_event(
                EventKind.EXECUTION_REQUESTED,
                task_id=task.id,
                idempotency_key=f"task-{task.id}:attempt-1",
            )
        )
        u.commit()
    engine.dispose()
    return task.id


def test_startup_reconciles_before_serving(config_dir: Path, tmp_path: Path) -> None:

    database_url = f"sqlite:///{tmp_path / 'fieldpilot.db'}"
    task_id = seed_interrupted_request(database_url)

    app = create_app(Settings(_env_file=None, config_dir=config_dir, database_url=database_url))

    report = app.state.runtime.reconciliation
    assert report.failed == (task_id,)
    assert report.simulator_state_resumed is False
    with SqlUnitOfWork(create_db_engine(database_url)) as u:
        assert u.tasks.get(task_id).status is TaskStatus.FAILED
        assert u.events.find_unclosed_execution_requests() == []


# --- D010 / D036: demo-only revert window override --------------------------


def app_with(config_dir: Path, **env: Any) -> Any:
    settings = Settings(_env_file=None, config_dir=config_dir, database_url="sqlite://", **env)
    return create_app(settings)


def override_events(app: Any) -> list[Any]:
    with app.state.runtime.uow() as u:
        return list(u.events.list(kind=EventKind.CONFIG_OVERRIDE))


def test_demo_profile_accepts_the_override_and_logs_the_shortening(config_dir: Path) -> None:
    app = app_with(config_dir, app_profile="demo", demo_revert_window_seconds=600)

    window = app.state.runtime.revert_window
    assert (window.seconds, window.configured_seconds, window.overridden) == (600, 21600, True)
    [event] = override_events(app)
    assert event.inputs == {
        "setting": "revert_window_seconds",
        "configured_seconds": 21600,
        "override_seconds": 600,
        "app_profile": "demo",
    }


@pytest.mark.parametrize("profile", ["dev", "prod"])
def test_any_other_profile_refuses_to_start_with_the_override(
    config_dir: Path, profile: str
) -> None:
    with pytest.raises(ConfigError, match="only when APP_PROFILE=demo"):
        app_with(config_dir, app_profile=profile, demo_revert_window_seconds=600)


def test_the_default_profile_refuses_to_start_with_the_override(config_dir: Path) -> None:
    with pytest.raises(ConfigError, match="APP_PROFILE is 'dev'"):
        app_with(config_dir, demo_revert_window_seconds=600)


@pytest.mark.parametrize("seconds", [0, -5])
def test_the_override_must_be_positive(config_dir: Path, seconds: int) -> None:
    with pytest.raises(ConfigError, match="positive integer"):
        app_with(config_dir, app_profile="demo", demo_revert_window_seconds=seconds)


def test_the_override_can_only_shorten_the_window(config_dir: Path) -> None:
    with pytest.raises(ConfigError, match="can only shorten"):
        app_with(config_dir, app_profile="demo", demo_revert_window_seconds=21601)


def test_an_override_equal_to_the_configured_window_is_accepted(config_dir: Path) -> None:
    app = app_with(config_dir, app_profile="demo", demo_revert_window_seconds=21600)

    assert app.state.runtime.revert_window.seconds == 21600


def test_demo_profile_without_the_override_keeps_the_configured_window(config_dir: Path) -> None:
    app = app_with(config_dir, app_profile="demo")

    assert app.state.runtime.revert_window.seconds == 21600
    assert app.state.runtime.revert_window.overridden is False
    assert override_events(app) == []


def test_the_override_is_read_from_the_environment(
    config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_PROFILE", "prod")
    monkeypatch.setenv("DEMO_REVERT_WINDOW_SECONDS", "600")

    with pytest.raises(ConfigError, match="APP_PROFILE is 'prod'"):
        app_with(config_dir)
