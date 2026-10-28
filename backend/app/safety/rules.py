"""Safety rules as pure functions: no I/O, no clock, no database.

Every rule receives the proposal, a read-only `SafetyContext` and the
`SafetyLimits`, and returns a `RuleViolation` or None. A value equal to a
limit is allowed; only values strictly beyond it violate. Missing input is a
violation, never an assumed pass (D027).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain.enums import ActionType
from app.domain.proposals import ProposedAction
from app.domain.units import pct_of_field_capacity
from app.domain.violations import RuleCode, RuleViolation

# Actions that add water to a zone: subject to every irrigation rule.
IRRIGATION_ACTIONS = frozenset({ActionType.IRRIGATION, ActionType.EXTRA_IRRIGATION})
# Actions that move a date on the calendar: subject to the shift limit (D026).
CALENDAR_ACTIONS = frozenset(
    {ActionType.CALENDAR_SHIFT, ActionType.PLANTING_DATE_CHANGE, ActionType.HARVEST_TIMING}
)
# Outside the emergency stop's scope: they change nothing physical or planned (D022).
INFORMATIONAL_ACTIONS = frozenset({ActionType.STRESS_ALERT, ActionType.STAGE_REPORT})
# Inside the scope but exempt: closing a valve can only reduce risk (D022).
EMERGENCY_STOP_EXEMPT = frozenset({ActionType.STOP_IRRIGATION})

_HOUR = timedelta(hours=1)


@dataclass(frozen=True)
class SafetyLimits:
    """Numeric limits from config/safety.yaml (D001, D026)."""

    max_irrigation_mm_per_zone_day: float
    rain_skip_threshold_mm_24h: float
    min_irrigation_interval_hours: float
    max_moisture_pct_fc: float
    max_calendar_shift_days: float


@dataclass(frozen=True)
class SafetyContext:
    """Read-only snapshot of the field, built by the caller before evaluation."""

    emergency_stop_active: bool
    irrigated_mm_on_day: float  # executed + scheduled, same zone, day of scheduled_for
    last_irrigation_at: datetime | None
    soil_moisture_vwc: float | None  # raw volumetric %, converted by the rule (D015)
    field_capacity_vwc: float | None
    rain_forecast_mm_24h: float | None


Rule = Callable[[ProposedAction, SafetyContext, SafetyLimits], RuleViolation | None]


def check_emergency_stop(
    action: ProposedAction, ctx: SafetyContext, limits: SafetyLimits
) -> RuleViolation | None:
    """Block everything that adds water or changes the plan while the stop is active."""
    if not ctx.emergency_stop_active:
        return None
    if action.action_type in INFORMATIONAL_ACTIONS | EMERGENCY_STOP_EXEMPT:
        return None
    return RuleViolation(RuleCode.EMERGENCY_STOP_ACTIVE, {"action_type": str(action.action_type)})


def check_daily_irrigation_cap(
    action: ProposedAction, ctx: SafetyContext, limits: SafetyLimits
) -> RuleViolation | None:
    if action.action_type not in IRRIGATION_ACTIONS:
        return None
    volume = _positive_number(action, "volume_mm")
    if isinstance(volume, RuleViolation):
        return volume
    total = ctx.irrigated_mm_on_day + volume
    if total > limits.max_irrigation_mm_per_zone_day:
        return RuleViolation(
            RuleCode.DAILY_IRRIGATION_CAP_EXCEEDED,
            {
                "total_mm": total,
                "already_mm": ctx.irrigated_mm_on_day,
                "volume_mm": volume,
                "limit_mm": limits.max_irrigation_mm_per_zone_day,
            },
        )
    return None


def check_rain_forecast(
    action: ProposedAction, ctx: SafetyContext, limits: SafetyLimits
) -> RuleViolation | None:
    if action.action_type not in IRRIGATION_ACTIONS:
        return None
    if ctx.rain_forecast_mm_24h is None:
        return _missing("rain_forecast_mm_24h")
    if ctx.rain_forecast_mm_24h > limits.rain_skip_threshold_mm_24h:
        return RuleViolation(
            RuleCode.RAIN_FORECAST_ABOVE_LIMIT,
            {
                "forecast_mm": ctx.rain_forecast_mm_24h,
                "limit_mm": limits.rain_skip_threshold_mm_24h,
            },
        )
    return None


def check_irrigation_interval(
    action: ProposedAction, ctx: SafetyContext, limits: SafetyLimits
) -> RuleViolation | None:
    """Measured from the proposal's own `scheduled_for`, so next-day plans are judged then."""
    if action.action_type not in IRRIGATION_ACTIONS or ctx.last_irrigation_at is None:
        return None
    hours = (action.scheduled_for - ctx.last_irrigation_at) / _HOUR
    if hours < limits.min_irrigation_interval_hours:
        return RuleViolation(
            RuleCode.IRRIGATION_INTERVAL_TOO_SHORT,
            {"hours_since_last": hours, "min_hours": limits.min_irrigation_interval_hours},
        )
    return None


def check_moisture(
    action: ProposedAction, ctx: SafetyContext, limits: SafetyLimits
) -> RuleViolation | None:
    """Compares percent of field capacity, never the raw sensor value (D015)."""
    if action.action_type not in IRRIGATION_ACTIONS:
        return None
    if ctx.soil_moisture_vwc is None:
        return _missing("soil_moisture_vwc")
    if ctx.field_capacity_vwc is None or ctx.field_capacity_vwc <= 0:
        return _missing("field_capacity_vwc")
    pct_fc = pct_of_field_capacity(ctx.soil_moisture_vwc, ctx.field_capacity_vwc)
    if pct_fc > limits.max_moisture_pct_fc:
        return RuleViolation(
            RuleCode.MOISTURE_ABOVE_LIMIT,
            {"moisture_pct_fc": pct_fc, "limit_pct_fc": limits.max_moisture_pct_fc},
        )
    return None


def check_calendar_shift(
    action: ProposedAction, ctx: SafetyContext, limits: SafetyLimits
) -> RuleViolation | None:
    """Earlier and later shifts count the same (D026)."""
    if action.action_type not in CALENDAR_ACTIONS:
        return None
    shift = _as_number(action.params.get("shift_days"))
    if shift is None:
        return _missing("shift_days")
    days = abs(shift)
    if days > limits.max_calendar_shift_days:
        return RuleViolation(
            RuleCode.CALENDAR_SHIFT_TOO_LARGE,
            {"shift_days": days, "limit_days": limits.max_calendar_shift_days},
        )
    return None


# The emergency stop runs first so its code leads the verdict (D022).
ALL_RULES: tuple[Rule, ...] = (
    check_emergency_stop,
    check_daily_irrigation_cap,
    check_rain_forecast,
    check_irrigation_interval,
    check_moisture,
    check_calendar_shift,
)


def evaluate_rules(
    action: ProposedAction, ctx: SafetyContext, limits: SafetyLimits
) -> tuple[RuleViolation, ...]:
    """Every violation, in rule order. Empty means the action is within all limits."""
    results = (rule(action, ctx, limits) for rule in ALL_RULES)
    return tuple(violation for violation in results if violation is not None)


def _missing(name: str) -> RuleViolation:
    return RuleViolation(RuleCode.MISSING_INPUT, {"input": name})


def _as_number(value: object) -> float | None:
    """The value as a float, or None if it is not a real number (booleans excluded)."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _positive_number(action: ProposedAction, name: str) -> float | RuleViolation:
    value = _as_number(action.params.get(name))
    if value is None or value <= 0:
        return _missing(name)
    return value
