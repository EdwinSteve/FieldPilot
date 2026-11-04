"""Load and cross-validate every configuration file at startup, agent prompts included.

Any inconsistency raises ConfigError, and `create_app()` lets it propagate,
so the application never runs on an unsafe configuration (D005, D006, D025).
`start_runtime` then opens the database and reconciles interrupted
executions before any request is served (D013).
"""

import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from app.actuation.config import ActuationConfig, load_actuation_config
from app.actuation.emergency import StoredEmergencyStop
from app.actuation.simulated import SimulatedActuator
from app.agent.catalog import SHOPPER, load_agent_catalog
from app.agent.loop import Subagent
from app.autonomy.messages import MessageCatalog, load_message_catalog
from app.autonomy.policy import AutonomyPolicy, load_autonomy_policy, validate_stage_overrides
from app.domain.enums import EventKind
from app.domain.errors import ConfigError
from app.domain.models import Event
from app.identity.config import IdentityConfig, load_identity_config
from app.identity.tokens import MIN_SECRET_LENGTH
from app.market.config import MarketConfig, load_market_config
from app.persistence.db import create_db_engine, init_schema
from app.persistence.ports import UnitOfWork
from app.persistence.unit_of_work import SqlUnitOfWork
from app.phenology.catalog import CatalogError, CropCatalog, load_crop_catalog
from app.safety.limits import load_safety_limits
from app.safety.rules import SafetyLimits
from app.satellite.config import ImagingConfig, load_imaging_config
from app.services.agronomy import SoilProbe, load_soil_probe
from app.services.clock import load_or_start_clock
from app.services.reconciliation import ReconciliationReport, reconcile_executions
from app.services.sensor_kit import SensorKit, load_sensor_kit
from app.services.simulation import ensure_simulated
from app.settings import Settings
from app.simulator.clock import SimClock, WallClock, system_wall_clock
from app.simulator.field import FieldSimulator

UowFactory = Callable[[], UnitOfWork]


@dataclass(frozen=True)
class RuntimeConfig:
    policy: AutonomyPolicy
    limits: SafetyLimits
    crops: CropCatalog
    messages: MessageCatalog  # in APP_LANGUAGE
    messages_es: MessageCatalog  # always Spanish, for the API's `_es` fields
    actuation: ActuationConfig
    imaging: ImagingConfig
    subagents: tuple[Subagent, ...]
    identity: IdentityConfig
    market: MarketConfig  # D085
    shopper: Subagent  # the customer's shopping assistant (D085)
    demo_field: SensorKit  # a demo plot's simulated sensors (D089)
    soil_probe: SoilProbe  # the agronomist's soil (D093)


def load_runtime_config(config_dir: Path, language: str = "en") -> RuntimeConfig:
    """Load autonomy, safety, crop, message and actuation configuration from `config_dir`.

    `language` picks the message catalogue and the agent prompts (D084).
    """
    policy = load_autonomy_policy(config_dir / "autonomy.yaml")
    limits = load_safety_limits(config_dir / "safety.yaml")
    try:
        # The crop catalog takes the moisture ceiling from safety.yaml, not a copy.
        crops = load_crop_catalog(config_dir / "crops", limits.max_moisture_pct_fc)
    except CatalogError as error:
        raise ConfigError(str(error)) from error
    validate_stage_overrides(policy, crops)
    messages = load_message_catalog(config_dir / "messages" / f"{language}.yaml")
    # The `_es` fields of the API stay Spanish whatever the language (D084).
    messages_es = (
        messages if language == "es" else load_message_catalog(config_dir / "messages" / "es.yaml")
    )
    actuation = load_actuation_config(config_dir / "actuation.yaml")
    return RuntimeConfig(
        policy=policy,
        limits=limits,
        crops=crops,
        messages=messages,
        messages_es=messages_es,
        actuation=actuation,
        imaging=load_imaging_config(config_dir / "imaging.yaml"),
        subagents=load_agent_catalog(config_dir / "agents", language=language),  # D053, D055, D084
        identity=load_identity_config(config_dir / "identity.yaml"),  # D082
        market=load_market_config(config_dir / "market.yaml"),
        shopper=load_agent_catalog(config_dir / "agents", (SHOPPER,), language=language)[0],
        demo_field=load_sensor_kit(config_dir / "demo_field.yaml"),
        soil_probe=load_soil_probe(config_dir / "soil_probe.yaml"),
    )


@dataclass(frozen=True)
class RevertWindowSetting:
    """The effective revert window and, when shortened for the demo, by how much."""

    seconds: int
    configured_seconds: int  # revert_window_seconds in autonomy.yaml
    overridden: bool

    @property
    def window(self) -> timedelta:
        return timedelta(seconds=self.seconds)


def resolve_revert_window(settings: Settings, policy: AutonomyPolicy) -> RevertWindowSetting:
    """Apply DEMO_REVERT_WINDOW_SECONDS only where D010 and D036 allow it."""
    configured = policy.revert_window_seconds
    override = settings.demo_revert_window_seconds
    if override is None:
        return RevertWindowSetting(configured, configured, overridden=False)
    if settings.app_profile != "demo":
        raise ConfigError(
            f"DEMO_REVERT_WINDOW_SECONDS is set but APP_PROFILE is {settings.app_profile!r}; "
            "it is honoured only when APP_PROFILE=demo (D010)"
        )
    if override <= 0:
        raise ConfigError("DEMO_REVERT_WINDOW_SECONDS must be a positive integer (D010)")
    if override > configured:
        raise ConfigError(
            f"DEMO_REVERT_WINDOW_SECONDS {override} exceeds revert_window_seconds "
            f"{configured}; the override can only shorten the window (D036)"
        )
    return RevertWindowSetting(override, configured, overridden=True)


@dataclass(frozen=True)
class AuthSetting:
    """Whether requests need a token, and the key that signs access tokens (D082)."""

    required: bool
    signing_key: str = field(repr=False)


def resolve_auth(settings: Settings) -> AuthSetting:
    """AUTH_REQUIRED=0 only under the demo profile; a configured key under prod."""
    if not settings.auth_required and settings.app_profile != "demo":
        raise ConfigError(
            f"AUTH_REQUIRED=0 is set but APP_PROFILE is {settings.app_profile!r}; "
            "it is honoured only when APP_PROFILE=demo (D082)"
        )
    configured = settings.auth_jwt_secret
    if configured is None:
        if settings.app_profile == "prod":
            raise ConfigError("APP_PROFILE=prod requires AUTH_JWT_SECRET (D082)")
        # Sessions then end when the process stops, which dev and demo accept.
        return AuthSetting(settings.auth_required, secrets.token_urlsafe(48))
    key = configured.get_secret_value()
    if len(key) < MIN_SECRET_LENGTH:
        raise ConfigError(f"AUTH_JWT_SECRET needs at least {MIN_SECRET_LENGTH} characters")
    return AuthSetting(settings.auth_required, key)


@dataclass(frozen=True)
class Runtime:
    """Long-lived collaborators built once at startup and shared by the services."""

    uow: UowFactory
    clock: SimClock
    simulator: FieldSimulator
    actuator: SimulatedActuator
    reconciliation: ReconciliationReport
    revert_window: RevertWindowSetting


def start_runtime(
    settings: Settings,
    config: RuntimeConfig,
    revert_window: RevertWindowSetting,
    wall: WallClock = system_wall_clock,
) -> Runtime:
    """Open the database, restore the clock, and reconcile before serving (D013, D014).

    The simulator starts empty: its state is not resumed after a restart, and
    the reconciliation report says so. After reconciliation each zone is
    rebuilt from its latest moisture reading (§4.10); zones created later
    join on the next simulation tick.
    """
    engine = create_db_engine(settings.database_url)
    init_schema(engine)

    def uow() -> UnitOfWork:
        return SqlUnitOfWork(engine)

    clock = load_or_start_clock(uow, wall, default_start=wall())
    simulator = FieldSimulator(start=clock.now())
    actuator = SimulatedActuator(
        simulator, StoredEmergencyStop(uow), clock, config.actuation.irrigation_rate_mm_per_h
    )
    report = reconcile_executions(uow, clock, actuator, config.messages)
    ensure_simulated(uow, simulator)  # §4.10: rebuilt from the latest readings
    if revert_window.overridden:
        _log_override(uow, clock, settings, revert_window)
    return Runtime(uow, clock, simulator, actuator, report, revert_window)


def _log_override(
    uow: UowFactory, clock: SimClock, settings: Settings, setting: RevertWindowSetting
) -> None:
    """Every startup with a shortened window says so in the event log (D010)."""
    with uow() as u:
        u.events.append(
            Event(
                kind=EventKind.CONFIG_OVERRIDE,
                actor="system:startup",
                reason=f"Revert window shortened for the demo: {setting.configured_seconds} s "
                f"-> {setting.seconds} s (DEMO_REVERT_WINDOW_SECONDS).",
                occurred_at=clock.now(),
                inputs={
                    "setting": "revert_window_seconds",
                    "configured_seconds": setting.configured_seconds,
                    "override_seconds": setting.seconds,
                    "app_profile": settings.app_profile,
                },
            )
        )
        u.commit()
