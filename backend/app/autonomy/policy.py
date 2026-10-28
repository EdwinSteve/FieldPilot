"""Autonomy policy loaded from config/autonomy.yaml, validated before the app starts."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.enums import ActionType, AutonomyLevel, strictness
from app.domain.errors import ConfigError
from app.phenology.catalog import CropCatalog

# Fixed in code on purpose (D005): editing the YAML alone can never release
# one of these types from farmer approval.
MANDATORY_APPROVAL: frozenset[ActionType] = frozenset(
    {
        ActionType.FERTILIZER,
        ActionType.AGROCHEMICAL,
        ActionType.PLANTING_DATE_CHANGE,
        ActionType.HARVEST_TIMING,
        ActionType.PRODUCT_LISTING,
        ActionType.PRICE_CHANGE,
        ActionType.CHEMICAL_INJECTION,
    }
)


@dataclass(frozen=True)
class AutonomyPolicy:
    defaults: Mapping[ActionType, AutonomyLevel]
    always_approval: frozenset[ActionType]
    revert_window_seconds: int  # stored now, used by the revert window in step 6

    def default_level(self, action_type: ActionType) -> AutonomyLevel:
        return self.defaults[action_type]


class _AutonomyFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    revert_window_seconds: int = Field(gt=0)
    always_approval: list[ActionType]
    defaults: dict[ActionType, AutonomyLevel]


def load_autonomy_policy(path: Path) -> AutonomyPolicy:
    """Read and validate the policy. Any problem raises ConfigError."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        parsed = _AutonomyFile.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise ConfigError(f"{path.name}: {error}") from error
    policy = AutonomyPolicy(
        defaults=dict(parsed.defaults),
        always_approval=frozenset(parsed.always_approval),
        revert_window_seconds=parsed.revert_window_seconds,
    )
    problems = _policy_problems(policy)
    if problems:
        raise ConfigError(f"{path.name}: " + "; ".join(problems))
    return policy


def validate_stage_overrides(policy: AutonomyPolicy, catalog: CropCatalog) -> None:
    """Refuse any crop stage override that relaxes a default level (D006).

    The gate would ignore a relaxing override anyway, but a catalog that
    tries to relax a level is a configuration error worth stopping for.
    """
    problems = [
        f"{crop.name}/{stage.name}: {action_type} {level} relaxes default "
        f"{policy.default_level(action_type)}"
        for crop in catalog.values()
        for stage in crop.stages
        for action_type, level in stage.autonomy.items()
        if strictness(level) < strictness(policy.default_level(action_type))
    ]
    if problems:
        raise ConfigError("stage overrides: " + "; ".join(problems))


def _policy_problems(policy: AutonomyPolicy) -> list[str]:
    problems: list[str] = []
    missing = sorted(set(ActionType) - set(policy.defaults))
    if missing:
        problems.append(f"no level for action types: {', '.join(missing)}")  # D025
    not_listed = sorted(MANDATORY_APPROVAL - policy.always_approval)
    if not_listed:
        problems.append(f"always_approval must include: {', '.join(not_listed)}")  # D005
    for action_type in sorted(MANDATORY_APPROVAL | policy.always_approval):
        level = policy.defaults.get(action_type)
        if level is not None and level is not AutonomyLevel.APPROVAL:
            problems.append(f"{action_type} must be approval, not {level}")  # D005
    return problems
