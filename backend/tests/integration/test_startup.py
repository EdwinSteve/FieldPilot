"""create_app() must refuse to start on an unsafe configuration (D005, D006, D025)."""

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.domain.enums import ActionType
from app.domain.errors import ConfigError
from app.main import create_app
from app.settings import Settings
from tests.builders import BRIEF_ALWAYS_APPROVAL
from tests.conftest import CONFIG_DIR


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
    create_app(Settings(_env_file=None, config_dir=config_dir))


def test_shipped_configuration_starts(config_dir: Path) -> None:
    app = create_app(Settings(_env_file=None, config_dir=config_dir))

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
