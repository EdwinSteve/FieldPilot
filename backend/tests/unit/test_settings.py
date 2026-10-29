import pytest
from pydantic import ValidationError

from app.settings import Settings


def test_mock_mode_needs_no_credentials() -> None:
    settings = Settings(_env_file=None, mock_llm=True)

    assert settings.mock_llm is True
    assert settings.muse_agent_model is None


def test_real_mode_without_credentials_fails_fast() -> None:
    with pytest.raises(ValidationError, match="MUSE_AGENT_MODEL"):
        Settings(_env_file=None, mock_llm=False)


def test_real_mode_with_credentials_is_accepted() -> None:
    settings = Settings(
        _env_file=None,
        mock_llm=False,
        muse_api_key="test-key",
        muse_api_base_url="https://example.invalid",
        muse_agent_model="test-model",
    )

    assert settings.muse_agent_model == "test-model"


def test_an_unknown_profile_is_rejected() -> None:
    with pytest.raises(ValidationError, match="app_profile"):
        Settings(_env_file=None, app_profile="staging")


def test_the_default_profile_is_dev_without_override() -> None:
    settings = Settings(_env_file=None)

    assert (settings.app_profile, settings.demo_revert_window_seconds) == ("dev", None)
