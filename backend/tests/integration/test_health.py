from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.main import create_app
from app.settings import Settings


def _settings(**overrides: object) -> Settings:
    base = Settings(_env_file=None, database_url="sqlite://")
    return base.model_copy(update=overrides)


def test_health_returns_ok_in_mock_mode() -> None:
    client = TestClient(create_app(_settings(mock_llm=True)))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mock_llm": True}


def test_health_reports_live_mode() -> None:
    """The flag follows the settings, so the dashboard shows the chat state up front (D072)."""
    settings = _settings(
        mock_llm=False,
        muse_api_key=SecretStr("[REDACTED]"),
        muse_api_base_url="https://api.meta.ai/v1",
        muse_agent_model="muse-spark-1.3",
        muse_segmentation_model="sam-3.1",
        muse_transcribe_model="muse-voice-transcribe-1.0",
    )
    client = TestClient(create_app(settings))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mock_llm": False}
