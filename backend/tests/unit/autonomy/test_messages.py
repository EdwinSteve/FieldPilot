from pathlib import Path
from typing import Any

import pytest
import yaml

from app.autonomy.messages import format_number, load_message_catalog
from app.domain.errors import ConfigError
from app.domain.violations import RuleCode, RuleViolation
from tests.conftest import CONFIG_DIR

SHIPPED = CONFIG_DIR / "messages" / "es.yaml"
CATALOG = load_message_catalog(SHIPPED)

# One realistic violation per code, with the params the rules actually produce.
EXAMPLES = {
    RuleCode.EMERGENCY_STOP_ACTIVE: RuleViolation(
        RuleCode.EMERGENCY_STOP_ACTIVE, {"action_type": "irrigation"}
    ),
    RuleCode.ALWAYS_APPROVAL_TYPE: RuleViolation(
        RuleCode.ALWAYS_APPROVAL_TYPE, {"action_type": "fertilizer"}
    ),
    RuleCode.DAILY_IRRIGATION_CAP_EXCEEDED: RuleViolation(
        RuleCode.DAILY_IRRIGATION_CAP_EXCEEDED,
        {"total_mm": 25.0, "already_mm": 15.0, "volume_mm": 10.0, "limit_mm": 20.0},
    ),
    RuleCode.RAIN_FORECAST_ABOVE_LIMIT: RuleViolation(
        RuleCode.RAIN_FORECAST_ABOVE_LIMIT, {"forecast_mm": 8.0, "limit_mm": 5.0}
    ),
    RuleCode.IRRIGATION_INTERVAL_TOO_SHORT: RuleViolation(
        RuleCode.IRRIGATION_INTERVAL_TOO_SHORT, {"hours_since_last": 11.98, "min_hours": 12.0}
    ),
    RuleCode.MOISTURE_ABOVE_LIMIT: RuleViolation(
        RuleCode.MOISTURE_ABOVE_LIMIT, {"moisture_pct_fc": 93.75, "limit_pct_fc": 85.0}
    ),
    RuleCode.CALENDAR_SHIFT_TOO_LARGE: RuleViolation(
        RuleCode.CALENDAR_SHIFT_TOO_LARGE, {"shift_days": 3.0, "limit_days": 2.0}
    ),
    RuleCode.MISSING_INPUT: RuleViolation(
        RuleCode.MISSING_INPUT, {"input": "rain_forecast_mm_24h"}
    ),
}


def test_every_rule_code_has_an_example_here() -> None:
    assert set(EXAMPLES) == set(RuleCode)


@pytest.mark.parametrize("code", list(RuleCode))
def test_every_code_renders_as_a_pending_approval_message(code: RuleCode) -> None:
    text = CATALOG.render(EXAMPLES[code])

    assert text.startswith("Pendiente de aprobación")
    assert "{" not in text


def test_rain_message_reads_as_agreed() -> None:
    text = CATALOG.render(EXAMPLES[RuleCode.RAIN_FORECAST_ABOVE_LIMIT])

    assert text == "Pendiente de aprobación por lluvia prevista (8 mm > 5 mm)"


def test_missing_input_names_the_input_in_spanish() -> None:
    text = CATALOG.render(EXAMPLES[RuleCode.MISSING_INPUT])

    assert "pronóstico de lluvia" in text
    assert "rain_forecast_mm_24h" not in text


def test_already_decided_label() -> None:
    assert CATALOG.label("already_decided", decided_at="28/10/2026 06:00") == (
        "Ya decidida el 28/10/2026 06:00"
    )


@pytest.mark.parametrize(
    ("value", "text"),
    [(20.0, "20"), (20.01, "20,01"), (5.0, "5"), (93.75, "93,75"), (11.98, "11,98")],
)
def test_numbers_use_a_decimal_comma_without_trailing_zeros(value: float, text: str) -> None:
    assert format_number(value) == text


def write(tmp_path: Path, raw: dict[str, Any]) -> Path:
    path = tmp_path / "es.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return path


def shipped_raw() -> dict[str, Any]:
    raw: dict[str, Any] = yaml.safe_load(SHIPPED.read_text(encoding="utf-8"))
    return raw


@pytest.mark.parametrize("code", list(RuleCode))
def test_a_code_without_a_message_refuses_to_load(tmp_path: Path, code: RuleCode) -> None:
    raw = shipped_raw()
    del raw["rules"][str(code)]

    with pytest.raises(ConfigError, match=f"no message for rule code {code}"):
        load_message_catalog(write(tmp_path, raw))


def test_missing_already_decided_label_refuses_to_load(tmp_path: Path) -> None:
    raw = shipped_raw()
    raw["labels"] = {}

    with pytest.raises(ConfigError, match="already_decided"):
        load_message_catalog(write(tmp_path, raw))


def test_unknown_rule_code_refuses_to_load(tmp_path: Path) -> None:
    raw = shipped_raw()
    raw["rules"]["made_up_rule"] = "Texto"

    with pytest.raises(ConfigError, match="made_up_rule"):
        load_message_catalog(write(tmp_path, raw))
