"""Application settings read from environment variables.

Secrets and model ids are never hardcoded; they come from the environment
(or a local `.env` file that is not committed).
"""

from pathlib import Path
from typing import Literal, Self

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration for the backend."""

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env",),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Mock mode is the default so nothing reaches the network by accident.
    mock_llm: bool = True
    muse_api_key: SecretStr | None = None
    muse_api_base_url: str | None = None
    muse_agent_model: str | None = None

    # D010: the demo override is honoured only under APP_PROFILE=demo; any
    # other profile with the variable set refuses to start (app/bootstrap.py).
    app_profile: Literal["dev", "demo", "prod"] = "dev"
    demo_revert_window_seconds: int | None = None

    database_url: str = f"sqlite:///{REPO_ROOT / 'backend' / 'fieldpilot.db'}"
    config_dir: Path = REPO_ROOT / "config"
    data_dir: Path = REPO_ROOT / "data"

    @model_validator(mode="after")
    def _require_credentials_outside_mock_mode(self) -> Self:
        if self.mock_llm:
            return self
        missing = [
            name
            for name, value in (
                ("MUSE_API_KEY", self.muse_api_key),
                ("MUSE_API_BASE_URL", self.muse_api_base_url),
                ("MUSE_AGENT_MODEL", self.muse_agent_model),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"MOCK_LLM=0 requires: {', '.join(missing)}")
        return self
