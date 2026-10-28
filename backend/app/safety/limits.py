"""Load and validate config/safety.yaml. Kept apart so rules.py never does I/O."""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.errors import ConfigError
from app.safety.rules import SafetyLimits


class _SafetyFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_irrigation_mm_per_zone_day: float = Field(ge=0)
    rain_skip_threshold_mm_24h: float = Field(ge=0)
    min_irrigation_interval_hours: float = Field(ge=0)
    max_moisture_pct_fc: float = Field(gt=0, le=100)
    max_calendar_shift_days: float = Field(ge=0)


def load_safety_limits(path: Path) -> SafetyLimits:
    """Read the limits. Missing, unknown, negative or out-of-range values raise ConfigError."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        parsed = _SafetyFile.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise ConfigError(f"{path.name}: {error}") from error
    return SafetyLimits(**parsed.model_dump())
