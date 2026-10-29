"""Load and cross-validate every configuration file at startup.

Any inconsistency raises ConfigError, and `create_app()` lets it propagate,
so the application never runs on an unsafe configuration (D005, D006, D025).
`start_runtime` then opens the database and reconciles interrupted
executions before any request is served (D013).
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.actuation.config import ActuationConfig, load_actuation_config
from app.actuation.emergency import StoredEmergencyStop
from app.actuation.simulated import SimulatedActuator
from app.autonomy.messages import MessageCatalog, load_message_catalog
from app.autonomy.policy import AutonomyPolicy, load_autonomy_policy, validate_stage_overrides
from app.domain.errors import ConfigError
from app.persistence.db import create_db_engine, init_schema
from app.persistence.ports import UnitOfWork
from app.persistence.unit_of_work import SqlUnitOfWork
from app.phenology.catalog import CatalogError, CropCatalog, load_crop_catalog
from app.safety.limits import load_safety_limits
from app.safety.rules import SafetyLimits
from app.services.clock import load_or_start_clock
from app.services.reconciliation import ReconciliationReport, reconcile_executions
from app.settings import Settings
from app.simulator.clock import SimClock, WallClock, system_wall_clock
from app.simulator.field import FieldSimulator

UowFactory = Callable[[], UnitOfWork]


@dataclass(frozen=True)
class RuntimeConfig:
    policy: AutonomyPolicy
    limits: SafetyLimits
    crops: CropCatalog
    messages: MessageCatalog
    actuation: ActuationConfig


def load_runtime_config(config_dir: Path) -> RuntimeConfig:
    """Load autonomy, safety, crop, message and actuation configuration from `config_dir`."""
    policy = load_autonomy_policy(config_dir / "autonomy.yaml")
    limits = load_safety_limits(config_dir / "safety.yaml")
    try:
        # The crop catalog takes the moisture ceiling from safety.yaml, not a copy.
        crops = load_crop_catalog(config_dir / "crops", limits.max_moisture_pct_fc)
    except CatalogError as error:
        raise ConfigError(str(error)) from error
    validate_stage_overrides(policy, crops)
    messages = load_message_catalog(config_dir / "messages" / "es.yaml")
    actuation = load_actuation_config(config_dir / "actuation.yaml")
    return RuntimeConfig(
        policy=policy, limits=limits, crops=crops, messages=messages, actuation=actuation
    )


@dataclass(frozen=True)
class Runtime:
    """Long-lived collaborators built once at startup and shared by the services."""

    uow: UowFactory
    clock: SimClock
    simulator: FieldSimulator
    actuator: SimulatedActuator
    reconciliation: ReconciliationReport


def start_runtime(
    settings: Settings, config: RuntimeConfig, wall: WallClock = system_wall_clock
) -> Runtime:
    """Open the database, restore the clock, and reconcile before serving (D013, D014).

    The simulator always starts empty: its state is not resumed after a
    restart, and the reconciliation report says so.
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
    return Runtime(uow, clock, simulator, actuator, report)
