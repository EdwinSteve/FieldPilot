"""Builds every service once, from the settings, the configuration and the runtime.

No global mutable state (principle 8): `create_app()` keeps the container on
`app.state`, and routes reach it through FastAPI dependencies. Mock mode
decides here, and only here, which model clients are real (D063).
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from app.agent.llm.mock import MockLLMClient
from app.agent.llm.muse import MuseClient
from app.agent.llm.ports import LLMClient
from app.autonomy.gate import AutonomyGate
from app.bootstrap import AuthSetting, Runtime, RuntimeConfig
from app.identity.access import AccessPolicy
from app.identity.passwords import Argon2Hasher
from app.identity.service import AuthService
from app.identity.tokens import JwtAccessTokens
from app.market.trace.passport import PassportService
from app.planning.ports import CropRecommender
from app.planning.setup import build_recommender
from app.planning.site_jobs import (
    DisabledSiteBuilder,
    SiteBuilder,
    SiteJobs,
    SubprocessSiteBuilder,
)
from app.planning.sites import FileSiteSource
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
from app.services.cycles import CycleService
from app.services.daily_cycle import DailyCycle
from app.services.due_tasks import DueTaskRunner
from app.services.execution import ExecutionService
from app.services.field_reader import StoredFieldReader
from app.services.gate_context import StoredGateContextProvider
from app.services.imagery_reader import StoredImageryReader
from app.services.phenology import PhenologyService
from app.services.planning import PlanningService
from app.services.plots import PlotService
from app.services.proposals import ProposalService
from app.services.queries import FarmQueries
from app.services.rain_forecast import PlotRainForecast
from app.services.revert import RevertService
from app.services.scenarios import ScenarioService
from app.services.ticker import SimulationTicker
from app.services.voice_chat import VoiceChatService
from app.settings import Settings
from app.simulator.clock import system_wall_clock
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
    auth_required: bool  # False only under APP_PROFILE=demo (D082)
    auth: AuthService
    access: AccessPolicy
    planning: PlanningService  # stage 1 (D079, D081)
    plots: PlotService  # plots and their site data (D083)
    cycles: CycleService  # the sowing and the harvest the farmer confirms (D083)
    passports: PassportService  # stage 3, first slice (D083)


def build_container(
    settings: Settings, config: RuntimeConfig, runtime: Runtime, auth: AuthSetting
) -> Container:
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
        config.crops,
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
    queries = FarmQueries(uow, clock, revert, config.messages, imagery, config.crops)

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
    recommender = build_recommender(settings.planner_dir, settings.planner_bundle)
    sites = FileSiteSource([settings.data_dir / "fixtures" / "planner", _sites_dir(settings)])
    planning = PlanningService(uow, clock, sites, recommender, config.crops)
    site_jobs = _site_jobs(settings, runtime)
    crop_names = _crop_names(recommender, config)
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
        auth_required=auth.required,
        auth=_auth_service(runtime, config, auth),
        access=AccessPolicy(uow),
        planning=planning,
        plots=PlotService(uow, clock, sites, site_jobs),
        cycles=CycleService(uow, clock, planning, config.crops, crop_names),
        passports=PassportService(uow, crop_names),
    )


def _site_jobs(settings: Settings, runtime: Runtime) -> SiteJobs:
    """Snapshots the backend builds go to data/planner/sites, never into the fixtures."""
    builder: SiteBuilder = (
        SubprocessSiteBuilder(settings.planner_dir)
        if settings.planner_site_builder == "subprocess"
        else DisabledSiteBuilder()
    )
    jobs = SiteJobs(runtime.uow, system_wall_clock, builder, _sites_dir(settings))
    jobs.recover()
    return jobs


def _sites_dir(settings: Settings) -> Path:
    return settings.planner_sites_dir or settings.data_dir / "planner" / "sites"


def _crop_names(recommender: CropRecommender, config: RuntimeConfig) -> dict[str, str]:
    """Spanish crop names for messages and passports: the planner's, then the catalogue's."""
    names = {card.crop: card.name_es for card in recommender.crops}
    for name, spec in config.crops.items():
        names.setdefault(name, spec.display_name.get("es", name))
    return names


def _auth_service(runtime: Runtime, config: RuntimeConfig, auth: AuthSetting) -> AuthService:
    """Identity runs on the wall clock: the simulated one must not expire sessions (D082)."""
    lifetime = timedelta(minutes=config.identity.access_token_minutes)
    return AuthService(
        runtime.uow,
        system_wall_clock,
        Argon2Hasher(),
        JwtAccessTokens(auth.signing_key, lifetime),
        config.identity,
    )


def _segmentation(settings: Settings) -> SegmentationProvider:
    if settings.mock_llm:
        return RecordedSegmentation(settings.data_dir / "fixtures" / "sam")
    return Sam31Segmentation.from_settings(settings)
