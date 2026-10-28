from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.autonomy.policy import (
    MANDATORY_APPROVAL,
    AutonomyPolicy,
    load_autonomy_policy,
    validate_stage_overrides,
)
from app.domain.enums import ActionType, AutonomyLevel
from app.domain.errors import ConfigError
from app.phenology.catalog import CropSpec
from tests.builders import BRIEF_ALWAYS_APPROVAL
from tests.conftest import CONFIG_DIR

SHIPPED = CONFIG_DIR / "autonomy.yaml"


def shipped_raw() -> dict[str, Any]:
    raw: dict[str, Any] = yaml.safe_load(SHIPPED.read_text(encoding="utf-8"))
    return raw


def write(tmp_path: Path, raw: dict[str, Any]) -> Path:
    path = tmp_path / "autonomy.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return path


def test_shipped_policy_has_the_agreed_levels() -> None:
    policy = load_autonomy_policy(SHIPPED)

    assert policy.revert_window_seconds == 21600
    assert policy.always_approval == MANDATORY_APPROVAL
    assert policy.default_level(ActionType.IRRIGATION) is AutonomyLevel.AUTONOMOUS
    assert policy.default_level(ActionType.EXTRA_IRRIGATION) is AutonomyLevel.NOTIFY
    assert policy.default_level(ActionType.STOP_IRRIGATION) is AutonomyLevel.AUTONOMOUS
    assert policy.default_level(ActionType.STRESS_ALERT) is AutonomyLevel.AUTONOMOUS
    assert policy.default_level(ActionType.STAGE_REPORT) is AutonomyLevel.AUTONOMOUS
    assert policy.default_level(ActionType.SCOUTING_VISIT) is AutonomyLevel.NOTIFY
    assert policy.default_level(ActionType.CALENDAR_SHIFT) is AutonomyLevel.NOTIFY


def test_mandatory_list_matches_the_brief() -> None:
    assert frozenset(BRIEF_ALWAYS_APPROVAL) == MANDATORY_APPROVAL


@pytest.mark.parametrize("action_type", BRIEF_ALWAYS_APPROVAL)
@pytest.mark.parametrize("level", ["autonomous", "notify"])
def test_mandatory_type_below_approval_is_refused(
    tmp_path: Path, action_type: ActionType, level: str
) -> None:
    raw = shipped_raw()
    raw["defaults"][str(action_type)] = level

    with pytest.raises(ConfigError, match=f"{action_type} must be approval"):
        load_autonomy_policy(write(tmp_path, raw))


@pytest.mark.parametrize("action_type", BRIEF_ALWAYS_APPROVAL)
def test_mandatory_type_missing_from_the_list_is_refused(
    tmp_path: Path, action_type: ActionType
) -> None:
    raw = shipped_raw()
    raw["always_approval"].remove(str(action_type))

    with pytest.raises(ConfigError, match=f"always_approval must include: {action_type}"):
        load_autonomy_policy(write(tmp_path, raw))


def test_extra_always_approval_type_must_also_default_to_approval(tmp_path: Path) -> None:
    raw = shipped_raw()
    raw["always_approval"].append("scouting_visit")  # its default is notify

    with pytest.raises(ConfigError, match="scouting_visit must be approval"):
        load_autonomy_policy(write(tmp_path, raw))


@pytest.mark.parametrize("action_type", sorted(ActionType))
def test_every_action_type_needs_a_level(tmp_path: Path, action_type: ActionType) -> None:
    raw = shipped_raw()
    del raw["defaults"][str(action_type)]

    with pytest.raises(ConfigError, match="no level for action types"):
        load_autonomy_policy(write(tmp_path, raw))


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda raw: raw["defaults"].update({"teleport": "approval"}), "teleport"),
        (lambda raw: raw["defaults"].update({"irrigation": "sometimes"}), "sometimes"),
        (
            lambda raw: raw["always_approval"].append("harvest_timing_change"),
            "harvest_timing_change",
        ),
        (lambda raw: raw.update({"revert_window_seconds": 0}), "revert_window_seconds"),
        (lambda raw: raw.update({"revert_window_seconds": -60}), "revert_window_seconds"),
        (lambda raw: raw.pop("revert_window_seconds"), "revert_window_seconds"),
        (lambda raw: raw.update({"surprise": 1}), "surprise"),
    ],
)
def test_malformed_policy_is_refused(tmp_path: Path, mutate: Any, message: str) -> None:
    raw = shipped_raw()
    mutate(raw)

    with pytest.raises(ConfigError, match=message):
        load_autonomy_policy(write(tmp_path, raw))


def test_missing_file_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_autonomy_policy(tmp_path / "autonomy.yaml")


# --- stage overrides at startup (D006) -----------------------------------


def with_override(
    maize: CropSpec, action_type: ActionType, level: AutonomyLevel
) -> dict[str, CropSpec]:
    stage = replace(maize.stages[0], autonomy={action_type: level})
    return {"maize": replace(maize, stages=(stage, *maize.stages[1:]))}


def test_shipped_catalog_overrides_are_accepted(maize: CropSpec) -> None:
    validate_stage_overrides(load_autonomy_policy(SHIPPED), {"maize": maize})


def test_override_that_relaxes_a_default_is_refused(maize: CropSpec) -> None:
    policy: AutonomyPolicy = load_autonomy_policy(SHIPPED)
    relaxing = with_override(maize, ActionType.EXTRA_IRRIGATION, AutonomyLevel.AUTONOMOUS)

    with pytest.raises(ConfigError, match="extra_irrigation autonomous relaxes default notify"):
        validate_stage_overrides(policy, relaxing)


@pytest.mark.parametrize("level", [AutonomyLevel.NOTIFY, AutonomyLevel.APPROVAL])
def test_override_equal_or_stricter_is_accepted(maize: CropSpec, level: AutonomyLevel) -> None:
    validate_stage_overrides(
        load_autonomy_policy(SHIPPED), with_override(maize, ActionType.EXTRA_IRRIGATION, level)
    )
