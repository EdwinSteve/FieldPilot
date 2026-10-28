"""Proposed actions and their content-derived idempotency key (D023)."""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime

from app.domain.enums import ActionType
from app.domain.models import Money

ParamValue = float | str
PROPOSAL_KEY_PREFIX = "proposal-"
_FLOAT_DECIMALS = 3


def proposal_key(
    action_type: ActionType,
    plot_id: int,
    zone_id: int | None,
    local_day: date,
    params: Mapping[str, ParamValue],
) -> str:
    """Key that identifies *what would happen in the field*, not how it was worded.

    Rationale, cost and proposer are deliberately excluded: an LLM rewords
    them on every retry, and including them would defeat idempotency.
    """
    canonical = json.dumps(
        {
            "action_type": str(action_type),
            "plot_id": plot_id,
            "zone_id": zone_id,
            "day": local_day.isoformat(),
            "params": {name: _canonical(value) for name, value in params.items()},
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return PROPOSAL_KEY_PREFIX + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ProposedAction:
    """An action the agent (or the farmer) wants to take. Only the gate decides on it."""

    action_type: ActionType
    plot_id: int
    zone_id: int | None
    scheduled_for: datetime
    params: Mapping[str, ParamValue]
    rationale: str
    estimated_cost: Money | None
    proposed_by: str
    proposal_key: str

    @classmethod
    def create(
        cls,
        *,
        action_type: ActionType,
        plot_id: int,
        zone_id: int | None,
        scheduled_for: datetime,
        local_day: date,
        params: Mapping[str, ParamValue],
        rationale: str,
        proposed_by: str,
        estimated_cost: Money | None = None,
    ) -> "ProposedAction":
        """Build a proposal with its key computed from content; callers never build keys."""
        if scheduled_for.tzinfo is None:
            raise ValueError("scheduled_for must be timezone-aware")
        return cls(
            action_type=action_type,
            plot_id=plot_id,
            zone_id=zone_id,
            scheduled_for=scheduled_for,
            params=dict(params),
            rationale=rationale,
            estimated_cost=estimated_cost,
            proposed_by=proposed_by,
            proposal_key=proposal_key(action_type, plot_id, zone_id, local_day, params),
        )


def _canonical(value: ParamValue) -> ParamValue:
    if isinstance(value, bool):
        raise TypeError("boolean parameters are not supported")
    if isinstance(value, int | float):
        return round(float(value), _FLOAT_DECIMALS)
    return value
