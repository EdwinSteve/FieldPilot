"""Load and cross-validate every configuration file at startup.

Any inconsistency raises ConfigError, and `create_app()` lets it propagate,
so the application never runs on an unsafe configuration (D005, D006, D025).
"""

from dataclasses import dataclass
from pathlib import Path

from app.autonomy.messages import MessageCatalog, load_message_catalog
from app.autonomy.policy import AutonomyPolicy, load_autonomy_policy, validate_stage_overrides
from app.domain.errors import ConfigError
from app.phenology.catalog import CatalogError, CropCatalog, load_crop_catalog
from app.safety.limits import load_safety_limits
from app.safety.rules import SafetyLimits


@dataclass(frozen=True)
class RuntimeConfig:
    policy: AutonomyPolicy
    limits: SafetyLimits
    crops: CropCatalog
    messages: MessageCatalog


def load_runtime_config(config_dir: Path) -> RuntimeConfig:
    """Load autonomy, safety, crop and message configuration from `config_dir`."""
    policy = load_autonomy_policy(config_dir / "autonomy.yaml")
    limits = load_safety_limits(config_dir / "safety.yaml")
    try:
        # The crop catalog takes the moisture ceiling from safety.yaml, not a copy.
        crops = load_crop_catalog(config_dir / "crops", limits.max_moisture_pct_fc)
    except CatalogError as error:
        raise ConfigError(str(error)) from error
    validate_stage_overrides(policy, crops)
    messages = load_message_catalog(config_dir / "messages" / "es.yaml")
    return RuntimeConfig(policy=policy, limits=limits, crops=crops, messages=messages)
