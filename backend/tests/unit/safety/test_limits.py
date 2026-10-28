from pathlib import Path
from typing import Any

import pytest
import yaml

from app.domain.errors import ConfigError
from app.safety.limits import load_safety_limits
from tests.builders import LIMITS

SHIPPED_SAFETY_FILE = Path(__file__).resolve().parents[4] / "config" / "safety.yaml"

VALID: dict[str, Any] = {
    "max_irrigation_mm_per_zone_day": 20,
    "rain_skip_threshold_mm_24h": 5,
    "min_irrigation_interval_hours": 12,
    "max_moisture_pct_fc": 85,
    "max_calendar_shift_days": 2,
}


def write(tmp_path: Path, content: Any) -> Path:
    path = tmp_path / "safety.yaml"
    path.write_text(yaml.safe_dump(content), encoding="utf-8")
    return path


def test_shipped_safety_file_has_the_agreed_limits() -> None:
    assert load_safety_limits(SHIPPED_SAFETY_FILE) == LIMITS


def test_valid_file_loads_every_limit(tmp_path: Path) -> None:
    assert load_safety_limits(write(tmp_path, VALID)) == LIMITS


@pytest.mark.parametrize("key", sorted(VALID))
def test_missing_key_refuses_to_load(tmp_path: Path, key: str) -> None:
    content = {k: v for k, v in VALID.items() if k != key}

    with pytest.raises(ConfigError, match=key):
        load_safety_limits(write(tmp_path, content))


@pytest.mark.parametrize("key", sorted(VALID))
def test_negative_value_refuses_to_load(tmp_path: Path, key: str) -> None:
    with pytest.raises(ConfigError, match=key):
        load_safety_limits(write(tmp_path, {**VALID, key: -1}))


@pytest.mark.parametrize("value", [0, 100.5])
def test_moisture_limit_must_be_a_percentage(tmp_path: Path, value: float) -> None:
    with pytest.raises(ConfigError, match="max_moisture_pct_fc"):
        load_safety_limits(write(tmp_path, {**VALID, "max_moisture_pct_fc": value}))


def test_unknown_key_refuses_to_load(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="max_irrigation_mm"):
        load_safety_limits(write(tmp_path, {**VALID, "max_irrigation_mm": 30}))


def test_non_numeric_value_refuses_to_load(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_safety_limits(write(tmp_path, {**VALID, "rain_skip_threshold_mm_24h": "five"}))


def test_missing_file_refuses_to_load(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"safety\.yaml"):
        load_safety_limits(tmp_path / "safety.yaml")


def test_malformed_yaml_refuses_to_load(tmp_path: Path) -> None:
    path = tmp_path / "safety.yaml"
    path.write_text("max_irrigation_mm_per_zone_day: [20", encoding="utf-8")

    with pytest.raises(ConfigError):
        load_safety_limits(path)
