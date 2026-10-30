"""An app on an in-memory database, with one plot like the demo farm."""

from collections.abc import Iterator
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agent.llm.ports import LLMClient
from app.container import Container
from app.domain.enums import SensorKind
from app.domain.models import CropCycle, Plot, Reading, Sensor, SimClockState, Zone
from app.main import create_app
from app.persistence.db import create_db_engine, init_schema
from app.persistence.unit_of_work import SqlUnitOfWork
from app.services.chat import ChatService
from app.services.daily_cycle import DailyCycle
from app.services.voice_chat import VoiceChatService
from app.settings import Settings
from app.voice.speech import SpeechToText


@dataclass(frozen=True)
class Farm:
    plot_id: int
    zone_id: int
    cycle_id: int


# The simulated clock is stored paused at this time, so tests never depend on the date.
START = datetime(2026, 10, 28, 11, 0, tzinfo=UTC)


@pytest.fixture
def app(tmp_path: Path) -> FastAPI:
    url = f"sqlite:///{tmp_path / 'api.db'}"
    engine = create_db_engine(url)
    init_schema(engine)
    with SqlUnitOfWork(engine) as u:
        u.sim_clock.save(SimClockState(START, START, speed_factor=1.0, paused=True))
        u.commit()
    engine.dispose()
    return create_app(Settings(_env_file=None, database_url=url, mock_llm=True))


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def container(app: FastAPI) -> Container:
    built: Container = app.state.container
    return built


@pytest.fixture
def farm(container: Container) -> Farm:
    uow, now = container.runtime.uow, container.runtime.clock.now()
    with uow() as u:
        plot = u.plots.add(Plot("Neiva", 2.93, -75.28, 2.0, now, utc_offset_hours=-5.0))
        assert plot.id is not None
        zone = u.zones.add(Zone(plot.id, "Zona 2", 0.5, 32.0, valve_id="v2"))
        assert zone.id is not None
        sensor = u.sensors.add(Sensor(zone.id, SensorKind.SOIL_MOISTURE, "%"))
        assert sensor.id is not None
        u.readings.add_many([Reading(sensor.id, 20.0, now)])
        cycle = u.cycles.add(CropCycle(plot.id, "maize", date(2026, 10, 1)))
        assert cycle.id is not None
        u.commit()
    container.ticker.tick()  # as the demo does after seeding: the simulator learns the zone
    return Farm(plot.id, zone.id, cycle.id)


def with_chat(app: FastAPI, llm: LLMClient, speech: SpeechToText | None = None) -> Container:
    """Swap in a chat (and voice) around a scripted model, as live mode would wire it."""
    container: Container = app.state.container
    chat = ChatService(container.runtime.uow, container.agent_deps(llm))
    voice = None if speech is None else VoiceChatService(chat, speech)
    app.state.container = replace(container, chat=chat, voice=voice)
    swapped: Container = app.state.container
    return swapped


def with_cycle(app: FastAPI, llm: LLMClient) -> Container:
    """Swap in a daily cycle around a scripted model."""
    container: Container = app.state.container

    def daily_cycle() -> DailyCycle:
        deps = container.agent_deps(llm)
        return DailyCycle(container.runtime.uow, deps, container.config.messages)

    app.state.container = replace(container, daily_cycle=daily_cycle)
    swapped: Container = app.state.container
    return swapped
