import logging

import pytest

from app.agent.llm.ports import LLMUnavailableError
from app.agent.llm.preflight import ModelCheck, check_models, run_preflight
from app.settings import Settings

KEY = "sk-test-not-a-real-key"
ALL = frozenset({"muse-spark-1.3", "sam-3.1", "muse-voice-transcribe-1.0"})


class FakeModels:
    def __init__(self, available: frozenset[str] | None) -> None:
        self._available = available

    def available_models(self) -> frozenset[str]:
        if self._available is None:
            raise LLMUnavailableError("AuthenticationError (HTTP 401)")
        return self._available


def _settings(**overrides: object) -> Settings:
    settings = Settings(
        _env_file=None,
        muse_api_key=KEY,
        muse_agent_model="muse-spark-1.3",
        muse_segmentation_model="sam-3.1",
        muse_transcribe_model="muse-voice-transcribe-1.0",
    )
    return settings.model_copy(update=overrides)


def _run(settings: Settings, available: frozenset[str] | None) -> bool:
    return run_preflight(settings, lambda _: FakeModels(available))


def test_check_models_flags_unset_and_unavailable_ids() -> None:
    checks = check_models({"A": "x", "B": "y", "C": None}, frozenset({"x"}))

    assert checks == (
        ModelCheck("A", "x", True),
        ModelCheck("B", "y", False),
        ModelCheck("C", None, False),
    )


def test_passes_when_every_model_is_available(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="preflight")

    assert _run(_settings(), ALL) is True
    assert "OK       MUSE_TRANSCRIBE_MODEL = muse-voice-transcribe-1.0" in caplog.messages
    assert all(KEY not in message for message in caplog.messages)


def test_fails_when_a_model_is_missing(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="preflight")

    assert _run(_settings(), frozenset({"muse-spark-1.3", "sam-3.1"})) is False
    assert "MISSING  MUSE_TRANSCRIBE_MODEL = muse-voice-transcribe-1.0" in caplog.messages


def test_fails_when_a_model_is_not_configured(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="preflight")

    assert _run(_settings(muse_segmentation_model=None), ALL) is False
    assert "MISSING  MUSE_SEGMENTATION_MODEL = (not set)" in caplog.messages


def test_fails_without_a_key(caplog: pytest.LogCaptureFixture) -> None:
    assert _run(_settings(muse_api_key=None), ALL) is False
    assert "MUSE_API_KEY and MUSE_AGENT_MODEL must be set in .env." in caplog.messages


def test_fails_when_the_api_refuses_the_key(caplog: pytest.LogCaptureFixture) -> None:
    assert _run(_settings(), None) is False
    assert caplog.messages == [
        "Model API unreachable: AuthenticationError (HTTP 401). Check MUSE_API_KEY in .env."
    ]
