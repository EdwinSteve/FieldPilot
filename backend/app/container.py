"""Builds every service once, from the settings, the configuration and the runtime.

No global mutable state (principle 8): `create_app()` keeps the container on
`app.state`, and routes reach it through FastAPI dependencies. Mock mode
decides here, and only here, which model clients are real (D063).
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from app.agent.llm.mock import MockLLMClient
from app.agent.llm.muse import MuseClient
from app.agent.llm.ports import LLMClient
from app.autonomy.gate import AutonomyGate
from app.bootstrap import Runtime, RuntimeConfig
from app.satellite.sam31 import Sam31Segmentation
from app.satellite.scenes import ImageryLoader
from app.satellite.segmentation import RecordedSegmentation, SegmentationProvider
from app.services.agent_outbox import StoredOutbox
from app.services.agent_proposals import GateProposer
from app.services.agent_session import AgentDeps
from app.services.agent_trace import EventLogTraceSink
from app.services.approvals import ApprovalService
from app.services.chat import ChatService
from app.services.clock import ClockService
from app.services.control import EmergencyStopService
from app.services.daily_cycle import DailyCycle
from app.services.due_tasks import DueTaskRunner
from app.services.execution import ExecutionService
from app.services.field_reader import StoredFieldReader
from app.services.gate_context import StoredGateContextProvider
from app.services.imagery_reader import StoredImageryReader
from app.services.phenology import PhenologyService
from app.services.proposals import ProposalService
from app.services.queries import FarmQueries
from app.services.rain_forecast import PlotRainForecast
from app.services.revert import RevertService
from app.services.scenarios import ScenarioService
from app.services.ticker import SimulationTicker
from app.services.voice_chat import VoiceChatService
from app.settings import Settings
from app.voice.muse import MuseVoiceTranscribe
from app.weather.fixture import FixtureForecast

# One recorded daily cycle per local day of the plot (D076).
MOCK_CYCLE_DIR = ("fixtures", "llm", "demo")


@dataclass(frozen=True)
class Container:
    runtime: Runtime
    config: RuntimeConfig
    mock_llm: bool  # from settings; the dashboard shows the chat state up front (D072)
    clock_service: ClockService
    emergency: EmergencyStopService
    proposals: ProposalService
    approvals: ApprovalService
    revert: RevertService
    queries: FarmQueries
    scenarios: ScenarioService
    ticker: SimulationTicker
    agent_deps: Callable[[LLMClient], AgentDeps]  # every agent service, around a given model
    cycle_llm: Callable[[date], LLMClient]  # the live client, or that day's replay (D063, D076)
    daily_cycle: Callable[[int], DailyCycle]  # for a plot, on its current local day
    chat: ChatService | None  # None under MOCK_LLM=1 (D063)
    voice: VoiceChatService | None


def build_container(settings: Settings, config: RuntimeConfig, runtime: Runtime) -> Container:
    uow, clock = runtime.uow, runtime.clock
    forecast = PlotRainForecast(
        uow, FixtureForecast.from_directory(settings.data_dir / "fixtures" / "open_meteo")
    )
    gate = AutonomyGate(config.policy, config.limits)
    context = StoredGateContextProvider(uow, forecast, config.crops)
    executor = ExecutionService(uow, clock, runtime.actuator, config.messages)
    proposals = ProposalService(
        uow, clock, gate, context, executor, config.messages, runtime.revert_window.window
    )
    due = DueTaskRunner(uow, gate, context, executor, config.messages)
    phenology = PhenologyService(uow, config.crops, clock)
    revert = RevertService(uow, clock, runtime.actuator)
    imagery = StoredImageryReader(  # one reader, so each scene is segmented once
        uow,
        ImageryLoader.from_directory(settings.data_dir / "satellite"),
        _segmentation(settings),
        config.imaging,
    )

    def agent_deps(llm: LLMClient) -> AgentDeps:
        return AgentDeps(
            llm=llm,
            reader=StoredFieldReader(uow, forecast, config.crops, clock),
            proposer=GateProposer(uow, proposals, config.messages),
            outbox=StoredOutbox(uow, clock, config.messages),
            trace=EventLogTraceSink(uow, clock),
            imagery=imagery,
            clock=clock,
            subagents=config.subagents,
            max_turns=settings.agent_max_turns,
            new_id=lambda: uuid.uuid4().hex,
        )

    live = None if settings.mock_llm else agent_deps(MuseClient.from_settings(settings))
    recordings = settings.data_dir.joinpath(*MOCK_CYCLE_DIR)
    queries = FarmQueries(uow, clock, revert, config.messages, imagery)

    def cycle_llm(day: date) -> LLMClient:
        """A fresh replay of that day's recording; a day never recorded replays nothing,
        so the cycle stops with FixtureExhaustedError (503), never with made-up answers."""
        if live is not None:
            return live.llm
        recording = recordings / f"{day.isoformat()}.json"
        return MockLLMClient.from_fixture(recording) if recording.is_file() else MockLLMClient([])

    def daily_cycle(plot_id: int) -> DailyCycle:
        llm = cycle_llm(queries.local_day(plot_id))
        return DailyCycle(uow, agent_deps(llm), config.messages)

    chat = None if live is None else ChatService(uow, live)
    voice = (
        None
        if chat is None
        else VoiceChatService(chat, MuseVoiceTranscribe.from_settings(settings))
    )
    return Container(
        runtime=runtime,
        config=config,
        mock_llm=settings.mock_llm,
        clock_service=ClockService(clock, uow),
        emergency=EmergencyStopService(uow, clock),
        proposals=proposals,
        approvals=ApprovalService(uow, clock, due),
        revert=revert,
        queries=queries,
        scenarios=ScenarioService(uow, clock, runtime.simulator),
        ticker=SimulationTicker(uow, clock, runtime.simulator, due, phenology),
        agent_deps=agent_deps,
        cycle_llm=cycle_llm,
        daily_cycle=daily_cycle,
        chat=chat,
        voice=voice,
    )


def _segmentation(settings: Settings) -> SegmentationProvider:
    if settings.mock_llm:
        return RecordedSegmentation(settings.data_dir / "fixtures" / "sam")
    return Sam31Segmentation.from_settings(settings)
