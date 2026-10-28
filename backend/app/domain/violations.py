"""Rule codes and violations. Codes are English; farmer-facing text lives in
the message catalog (config/messages/es.yaml), keyed by code."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum


class RuleCode(StrEnum):
    EMERGENCY_STOP_ACTIVE = "emergency_stop_active"
    ALWAYS_APPROVAL_TYPE = "always_approval_type"
    DAILY_IRRIGATION_CAP_EXCEEDED = "daily_irrigation_cap_exceeded"
    RAIN_FORECAST_ABOVE_LIMIT = "rain_forecast_above_limit"
    IRRIGATION_INTERVAL_TOO_SHORT = "irrigation_interval_too_short"
    MOISTURE_ABOVE_LIMIT = "moisture_above_limit"
    CALENDAR_SHIFT_TOO_LARGE = "calendar_shift_too_large"
    MISSING_INPUT = "missing_input"


@dataclass(frozen=True)
class RuleViolation:
    """A rule that did not pass, with the numbers behind it and no text."""

    code: RuleCode
    params: Mapping[str, float | str] = field(default_factory=dict)
