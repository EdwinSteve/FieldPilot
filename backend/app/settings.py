"""Application settings read from environment variables.

Secrets and model ids are never hardcoded; they come from the environment
(or a local `.env` file that is not committed).
"""

from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
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
    # Read from step 8; `make preflight` checks every configured id (D043).
    muse_segmentation_model: str | None = None
    muse_transcribe_model: str | None = None
    muse_timeout_seconds: float = Field(default=30.0, gt=0)
    # At least 2: the last-turn nudge follows turn max_turns - 1 (§4.8 rule 5).
    agent_max_turns: int = Field(default=12, ge=2)
    # D093: the agronomist leads the daily cycle; "pipeline" is the fixed order of D044.
    daily_cycle: Literal["orchestrated", "pipeline"] = "orchestrated"

    # D010: the demo override is honoured only under APP_PROFILE=demo; any
    # other profile with the variable set refuses to start (app/bootstrap.py).
    app_profile: Literal["dev", "demo", "prod"] = "dev"
    demo_revert_window_seconds: int | None = None

    # D082: every route needs a token. AUTH_REQUIRED=0 is honoured only under
    # APP_PROFILE=demo; AUTH_JWT_SECRET is required under APP_PROFILE=prod.
    auth_required: bool = True
    auth_jwt_secret: SecretStr | None = None

    # D084: the language of every farmer-facing text. English by default; the
    # Spanish catalogue, prompts and recorded answers are kept for APP_LANGUAGE=es.
    app_language: Literal["en", "es"] = "en"

    database_url: str = f"sqlite:///{REPO_ROOT / 'backend' / 'fieldpilot.db'}"
    config_dir: Path = REPO_ROOT / "config"
    data_dir: Path = REPO_ROOT / "data"
    # Stage 1 (D081): the planner's configs and models; PLANNER_BUNDLE pins one bundle.
    planner_dir: Path = REPO_ROOT / "planner"
    planner_bundle: Path | None = None
    # D083: how a new plot's site snapshot is built. "off" in CI and tests (no network).
    planner_site_builder: Literal["subprocess", "off"] = "subprocess"
    planner_sites_dir: Path | None = None  # where built snapshots go; data/planner/sites

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
