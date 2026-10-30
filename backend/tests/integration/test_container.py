"""The container wires every service once; mock mode decides which clients are real."""

from pydantic import SecretStr

from app.agent.llm.mock import MockLLMClient
from app.main import create_app
from app.services.daily_cycle import DailyCycle
from app.settings import Settings


def _settings(**overrides: object) -> Settings:
    base = Settings(_env_file=None, database_url="sqlite://")
    return base.model_copy(update=overrides)


def test_mock_mode_has_no_chat_and_replays_the_cycle() -> None:
    """D063: no canned chat; the daily cycle replays a fixture."""
    container = create_app(_settings(mock_llm=True)).state.container

    assert container.chat is None and container.voice is None
    assert isinstance(container.daily_cycle(), DailyCycle)
    first, second = container.cycle_llm(), container.cycle_llm()
    assert isinstance(first, MockLLMClient) and first is not second  # a fresh replay per run


def test_live_mode_wires_the_chat_and_voice_without_calling_the_network() -> None:
    settings = _settings(
        mock_llm=False,
        muse_api_key=SecretStr("sk-test-not-a-real-key"),
        muse_api_base_url="https://api.meta.ai/v1",
        muse_agent_model="muse-spark-1.3",
        muse_segmentation_model="sam-3.1",
        muse_transcribe_model="muse-voice-transcribe-1.0",
    )

    container = create_app(settings).state.container

    assert container.chat is not None and container.voice is not None
    assert container.cycle_llm() is container.cycle_llm()  # one live client


def test_startup_loads_imaging_and_the_agent_catalogue() -> None:
    config = create_app(_settings()).state.container.config

    assert config.imaging.segmentation_prompt == "brown patch"
    assert [a.name for a in config.subagents][:4] == [
        "monitoring",
        "imaging",
        "irrigation",
        "reporting",
    ]


def test_the_mock_fixtures_exist_in_data() -> None:
    settings = _settings()

    assert (settings.data_dir / "fixtures" / "llm" / "demo_day1.json").is_file()
    assert any((settings.data_dir / "fixtures" / "sam").glob("*.txt"))
