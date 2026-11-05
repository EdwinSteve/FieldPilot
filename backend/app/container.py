"""Builds every service once, from the settings, the configuration and the runtime.

No global mutable state (principle 8): `create_app()` keeps the container on
`app.state`, and routes reach it through FastAPI dependencies. Mock mode
decides here, and only here, which model clients are real (D063).
"""

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from app.agent.llm.mock import MockLLMClient
from app.agent.llm.muse import MuseClient
from app.agent.llm.ports import LLMClient
from app.autonomy.gate import AutonomyGate
from app.bootstrap import AuthSetting, Runtime, RuntimeConfig, UowFactory
from app.identity.access import AccessPolicy
from app.identity.models import Principal
from app.identity.passwords import Argon2Hasher
from app.identity.service import AuthService
from app.identity.tokens import JwtAccessTokens
from app.market.freshness import ClearancePolicy
from app.market.listings import ListingService
from app.market.orders import OrderService
from app.market.payments import MockPaymentGateway
from app.market.recommend.cart import CartSuggestionService
from app.market.recommend.service import RecommendationService
from app.market.store import StoreService
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
from app.services.agronomy import StoredAgronomy
from app.services.approvals import ApprovalService
from app.services.chat import ChatService
from app.services.clock import ClockService
from app.services.control import EmergencyStopService
from app.services.cycles import CycleService
from app.services.daily_cycle import Cycle, DailyCycle, OrchestratedCycle
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
from app.services.rain_forecast import PlotRainForecast, PlotWeatherService
from app.services.revert import RevertService
from app.services.scenarios import ScenarioService
from app.services.sensor_kit import SensorKitInstaller
from app.services.shopper import ShopperConversations, ShopperService, StoreShopperPort
from app.services.ticker import SimulationTicker
from app.services.voice_chat import VoiceChatService
from app.settings import Settings
from app.simulator.clock import SimClock, system_wall_clock
from app.voice.muse import MuseVoiceTranscribe
from app.weather.fixture import FixtureForecast

# One recorded daily cycle per local day of the plot (D076), per language (D084):
# demo/ holds the Spanish recordings, demo-en/ the same runs with English texts.
MOCK_CYCLE_DIRS = {"es": ("fixtures", "llm", "demo"), "en": ("fixtures", "llm", "demo-en")}


@dataclass(frozen=True)
class Container:
    runtime: Runtime
    config: RuntimeConfig
    mock_llm: bool  # from settings; the dashboard shows the chat state up front (D072)
    agent_model: str | None  # MUSE_AGENT_MODEL, for the live badge (D094)
    replay: dict[str, str | None] | None  # the replayed recording's label; None live (D094)
    daily_cycle_kind: str  # D093
    weather: PlotWeatherService  # the forecast the gate reads, for the UI (D095)
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
    daily_cycle: Callable[[int], Cycle]  # for a plot, on its current local day
    cycle_with: Callable[[LLMClient], Cycle]  # the configured cycle around a given model
    chat: ChatService | None  # None under MOCK_LLM=1 (D063)
    voice: VoiceChatService | None
    auth_required: bool  # False only under APP_PROFILE=demo (D082)
    auth: AuthService
    access: AccessPolicy
    planning: PlanningService  # stage 1 (D079, D081)
    plots: PlotService  # plots and their site data (D083)
    cycles: CycleService  # the sowing and the harvest the farmer confirms (D083)
    passports: PassportService  # stage 3, first slice (D083)
    listings: ListingService  # the farmer's and the warehouse's side (D085)
    store: StoreService  # the customer's side (D085)
    orders: OrderService
    recommendations: RecommendationService
    cart_suggestions: CartSuggestionService  # the assistant in the cart, no model (D087)
    shopper: ShopperService | None  # None under MOCK_LLM=1, as the chat (D063, D085)


def build_container(
    settings: Settings, config: RuntimeConfig, runtime: Runtime, auth: AuthSetting
) -> Container:
    uow, clock = runtime.uow, runtime.clock
    demo = settings.app_profile == "demo"  # stand-ins for a plot away from the fixtures (D089)
    fixture_forecast = FixtureForecast.from_directory(
        settings.data_dir / "fixtures" / "open_meteo", nearest_anywhere=demo
    )
    forecast = PlotRainForecast(uow, fixture_forecast)
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
        ImageryLoader.from_directory(settings.data_dir / "satellite", synthetic_stand_in=demo),
        _segmentation(settings),
        config.imaging,
        config.crops,
    )

    sites = FileSiteSource([settings.data_dir / "fixtures" / "planner", _sites_dir(settings)])
    agronomy = StoredAgronomy(uow, clock, config.soil_probe, sites)

    def agent_deps(llm: LLMClient) -> AgentDeps:
        return AgentDeps(
            llm=llm,
            reader=StoredFieldReader(uow, forecast, config.crops, clock, config.messages.language),
            proposer=GateProposer(uow, proposals, config.messages),
            outbox=StoredOutbox(uow, clock, config.messages),
            trace=EventLogTraceSink(uow, clock),
            imagery=imagery,
            clock=clock,
            subagents=config.subagents,
            max_turns=settings.agent_max_turns,
            new_id=lambda: uuid.uuid4().hex,
            agronomy=agronomy,
        )

    live = None if settings.mock_llm else agent_deps(MuseClient.from_settings(settings))
    recordings = settings.data_dir.joinpath(*MOCK_CYCLE_DIRS[settings.app_language])
    queries = FarmQueries(
        uow, clock, revert, config.messages, imagery, config.crops, config.messages_es
    )

    def cycle_llm(day: date) -> LLMClient:
        """A fresh replay of that day's recording; a day never recorded replays nothing,
        so the cycle stops with FixtureExhaustedError (503), never with made-up answers."""
        if live is not None:
            return live.llm
        recording = recordings / f"{day.isoformat()}.json"
        return MockLLMClient.from_fixture(recording) if recording.is_file() else MockLLMClient([])

    def cycle_with(llm: LLMClient) -> Cycle:
        kind = OrchestratedCycle if settings.daily_cycle == "orchestrated" else DailyCycle
        return kind(uow, agent_deps(llm), config.messages)

    def daily_cycle(plot_id: int) -> Cycle:
        return cycle_with(cycle_llm(queries.local_day(plot_id)))

    off_topic = config.messages.label("out_of_scope_farmer")
    chat = None if live is None else ChatService(uow, live, off_topic)
    voice = (
        None
        if chat is None
        else VoiceChatService(
            chat, MuseVoiceTranscribe.from_settings(settings), settings.app_language
        )
    )
    recommender = build_recommender(settings.planner_dir, settings.planner_bundle)
    crop_names = _crop_names(recommender, config)
    passports = PassportService(uow, config.messages, config.messages_es)
    access = AccessPolicy(uow)
    clearance = ClearancePolicy(config.market)
    listings = ListingService(uow, clock, config.market, access, clearance)
    listings.ensure_warehouses()  # the default warehouse in Bogotá, D.C. (D085)
    listings.expire_due()  # write off what passed its best-before day (D086)
    payments = MockPaymentGateway()
    store = StoreService(uow, clock, config.market, config.messages, payments, clearance)
    orders = OrderService(uow, clock, payments)
    recommendations = RecommendationService(uow, store, config.market)
    planning = PlanningService(uow, clock, sites, recommender, config.crops, crop_names)
    site_jobs = _site_jobs(settings, runtime)
    return Container(
        runtime=runtime,
        config=config,
        mock_llm=settings.mock_llm,
        agent_model=settings.muse_agent_model,
        replay=_replay_label(recordings) if settings.mock_llm else None,
        daily_cycle_kind=settings.daily_cycle,
        weather=PlotWeatherService(uow, fixture_forecast, clock),
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
        cycle_with=cycle_with,
        chat=chat,
        voice=voice,
        auth_required=auth.required,
        auth=_auth_service(runtime, config, auth),
        access=access,
        planning=planning,
        plots=PlotService(uow, clock, sites, site_jobs, config.messages, _sensor_kit(demo, config)),
        cycles=CycleService(uow, clock, planning, config.crops, crop_names),
        passports=passports,
        listings=listings,
        store=store,
        orders=orders,
        recommendations=recommendations,
        cart_suggestions=CartSuggestionService(recommendations, store, config.messages),
        shopper=_shopper(live, config, store, orders, recommendations, passports, clock, uow),
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


def _shopper(
    live: AgentDeps | None,
    config: RuntimeConfig,
    store: StoreService,
    orders: OrderService,
    recommendations: RecommendationService,
    passports: PassportService,
    clock: SimClock,
    uow: UowFactory,
) -> ShopperService | None:
    """The shopping assistant runs on the farm agent's model, or not at all in mock mode."""
    if live is None:
        return None

    def port_for(principal: Principal, run_id: str) -> StoreShopperPort:
        return StoreShopperPort(principal, store, orders, recommendations, passports, clock, run_id)

    return ShopperService(
        live.llm,
        config.shopper,
        live.max_turns,
        port_for,
        lambda: uuid.uuid4().hex,
        store.proposal,
        config.messages.label("out_of_scope_customer"),
        ShopperConversations(uow, clock),
    )


def _sensor_kit(demo: bool, config: RuntimeConfig) -> SensorKitInstaller | None:
    """Only a demo plot gets simulated sensors; a real one waits for its hardware (D089)."""
    if not demo:
        return None
    return SensorKitInstaller(
        config.demo_field, lambda n: config.messages.label("demo_zone", n=str(n))
    )


RECORDED_FILE = "RECORDED.json"  # written by make record-demo next to the days (D094)


def _replay_label(recordings: Path) -> dict[str, str | None]:
    """When and with which model the replay was recorded; unknown values stay None."""
    try:
        label = json.loads((recordings / RECORDED_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        label = {}
    return {key: _text(label.get(key)) for key in ("recorded_on", "model")}


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _sites_dir(settings: Settings) -> Path:
    return settings.planner_sites_dir or settings.data_dir / "planner" / "sites"


def _crop_names(recommender: CropRecommender, config: RuntimeConfig) -> dict[str, str]:
    """Crop names in APP_LANGUAGE (D084): the message catalogue, then each crop's YAML."""
    language = config.messages.language
    names = {card.crop: config.messages.crop_name(card.crop) for card in recommender.crops}
    for name, spec in config.crops.items():
        names.setdefault(name, spec.display_name.get(language, name))
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
