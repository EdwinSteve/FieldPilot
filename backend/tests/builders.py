"""Builders for proposals, safety contexts and limits used across test modules."""

from dataclasses import replace
from datetime import UTC, datetime

from app.domain.enums import ActionType
from app.domain.proposals import ParamValue, ProposedAction
from app.safety.rules import SafetyContext, SafetyLimits

NOW = datetime(2026, 10, 28, 6, 0, tzinfo=UTC)

LIMITS = SafetyLimits(
    max_irrigation_mm_per_zone_day=20.0,
    rain_skip_threshold_mm_24h=5.0,
    min_irrigation_interval_hours=12.0,
    max_moisture_pct_fc=85.0,
    max_calendar_shift_days=2.0,
)

# A context in which every rule passes for a 15 mm irrigation.
SAFE = SafetyContext(
    emergency_stop_active=False,
    irrigated_mm_on_day=0.0,
    last_irrigation_at=None,
    soil_moisture_vwc=20.0,
    field_capacity_vwc=40.0,
    rain_forecast_mm_24h=0.0,
)


def proposal(
    action_type: ActionType = ActionType.IRRIGATION,
    params: dict[str, ParamValue] | None = None,
    scheduled_for: datetime = NOW,
    zone_id: int | None = 2,
) -> ProposedAction:
    return ProposedAction.create(
        action_type=action_type,
        plot_id=1,
        zone_id=zone_id,
        scheduled_for=scheduled_for,
        local_day=scheduled_for.date(),
        params={"volume_mm": 15.0} if params is None else params,
        rationale="test",
        proposed_by="test",
    )


def context(**changes: object) -> SafetyContext:
    return replace(SAFE, **changes)  # type: ignore[arg-type]


# The brief's always-approval types, written out independently of
# MANDATORY_APPROVAL so a type dropped from the code makes its test fail
# instead of silently disappearing from the parametrization.
BRIEF_ALWAYS_APPROVAL = (
    ActionType.FERTILIZER,
    ActionType.AGROCHEMICAL,
    ActionType.PLANTING_DATE_CHANGE,
    ActionType.HARVEST_TIMING,  # harvest_timing_change in the brief (D024)
    ActionType.PRODUCT_LISTING,
    ActionType.PRICE_CHANGE,
    ActionType.CHEMICAL_INJECTION,
)
