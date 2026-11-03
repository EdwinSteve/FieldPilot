"""Load and validate config/identity.yaml."""

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.errors import ConfigError

MAX_PASSWORD_LENGTH = 128


class _IdentityFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    access_token_minutes: int = Field(gt=0, le=60)
    refresh_token_days: int = Field(gt=0, le=90)
    max_failed_logins: int = Field(gt=0)
    lockout_minutes: int = Field(gt=0)
    password_min_length: int = Field(ge=8, le=64)
    privacy_policy_version: str = Field(min_length=1)


@dataclass(frozen=True)
class IdentityConfig:
    access_token_minutes: int
    refresh_token_days: int
    max_failed_logins: int
    lockout_minutes: int
    password_min_length: int
    privacy_policy_version: str


def load_identity_config(path: Path) -> IdentityConfig:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        parsed = _IdentityFile.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise ConfigError(f"{path.name}: {error}") from error
    return IdentityConfig(**parsed.model_dump())
