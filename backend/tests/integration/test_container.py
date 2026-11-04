"""The container wires every service once; mock mode decides which clients are real."""

import shutil
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import SecretStr

from app.agent.llm.mock import MockLLMClient
from app.agent.llm.ports import FixtureExhaustedError
from app.container import MOCK_CYCLE_DIRS
from app.domain.enums import SensorKind
from app.domain.models import Plot, Reading, Sensor, Zone
from app.main import create_app
from app.persistence.db import create_db_engine, init_schema
from app.persistence.unit_of_work import SqlUnitOfWork
from app.services.daily_cycle import DailyCycle
from app.services.demo_seed import seed_demo_farm
from app.settings import Settings

START = datetime(2026, 10, 28, 11, 0, tzinfo=UTC)
DEMO_DAY_1, DEMO_DAY_2 = date(2026, 11, 2), date(2026, 11, 3)


def _settings(**overrides: object) -> Settings:
    base = Settings(_env_file=None, database_url="sqlite://")
    return base.model_copy(update=overrides)


def test_mock_mode_has_no_chat_and_replays_the_cycle() -> None:
    """D063: no canned chat; the daily cycle replays a fixture."""
    container = create_app(_settings(mock_llm=True)).state.container

    assert container.chat is None and container.voice is None
    first, second = container.cycle_llm(DEMO_DAY_1), container.cycle_llm(DEMO_DAY_1)
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
    assert container.cycle_llm(DEMO_DAY_1) is container.cycle_llm(DEMO_DAY_2)  # one live client


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

    recordings = settings.data_dir / "fixtures" / "llm" / "demo"
    assert sorted(p.name for p in recordings.glob("*.json")) == [
        "2026-11-02.json",
        "2026-11-03.json",
        "RECORDED.json",  # the replay's label (D094)
    ]
    assert any((settings.data_dir / "fixtures" / "sam").glob("*.txt"))


def test_startup_rebuilds_the_simulator_from_stored_readings(tmp_path: Path) -> None:
    """§4.10, D014: after a restart the simulator knows every zone with a reading."""
    url = f"sqlite:///{tmp_path / 'farm.db'}"
    engine = create_db_engine(url)
    init_schema(engine)
    with SqlUnitOfWork(engine) as u:
        plot = u.plots.add(Plot("Neiva", 2.93, -75.28, 2.0, START, utc_offset_hours=-5.0))
        assert plot.id is not None
        measured = u.zones.add(Zone(plot.id, "Zona 2", 0.5, 32.0, valve_id="v2"))
        unmeasured = u.zones.add(Zone(plot.id, "Zona 3", 0.5, 32.0, valve_id="v3"))
        assert measured.id is not None and unmeasured.id is not None
        sensor = u.sensors.add(Sensor(measured.id, SensorKind.SOIL_MOISTURE, "%"))
        assert sensor.id is not None
        u.readings.add_many([Reading(sensor.id, 20.0, START)])
        u.commit()
    engine.dispose()

    simulator = create_app(_settings(database_url=url)).state.container.runtime.simulator

    assert simulator.simulates(measured.id)
    assert not simulator.simulates(unmeasured.id)  # no reading: never a guessed start (D019)


def test_mock_mode_replays_the_recording_of_the_plots_local_day(tmp_path: Path) -> None:
    """D076: one recording per local day; a day never recorded replays nothing.

    The English recordings are replayed by default (D084).
    """
    data = tmp_path / "data"
    shutil.copytree(Settings(_env_file=None).data_dir, data)
    recordings = data.joinpath(*MOCK_CYCLE_DIRS["en"])
    shutil.rmtree(recordings, ignore_errors=True)
    recordings.mkdir(parents=True)
    (recordings / "2026-11-02.json").write_text(
        '{"responses": [{"text": "day one"}]}', encoding="utf-8"
    )
    container = create_app(_settings(data_dir=data)).state.container

    recorded = container.cycle_llm(DEMO_DAY_1)
    missing = container.cycle_llm(DEMO_DAY_2)

    assert recorded.complete("s", [], []).text == "day one"
    with pytest.raises(FixtureExhaustedError):
        missing.complete("s", [], [])


def test_the_daily_cycle_uses_the_plots_current_local_day(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'demo.db'}"
    plot_id = seed_demo_farm(url).plot_id
    container = create_app(_settings(database_url=url)).state.container

    assert container.queries.local_day(plot_id) == DEMO_DAY_1
    assert isinstance(container.daily_cycle(plot_id), DailyCycle)
