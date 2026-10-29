"""Actuation settings loaded from config/actuation.yaml (D038)."""

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.errors import ConfigError


@dataclass(frozen=True)
class ActuationConfig:
    irrigation_rate_mm_per_h: float


class _ActuationFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    irrigation_rate_mm_per_h: float = Field(gt=0)


def load_actuation_config(path: Path) -> ActuationConfig:
    """Read and validate the file. Any problem raises ConfigError."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        parsed = _ActuationFile.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise ConfigError(f"{path.name}: {error}") from error
    return ActuationConfig(irrigation_rate_mm_per_h=parsed.irrigation_rate_mm_per_h)
