from datetime import date, datetime, timedelta

import pytest

from app.domain.enums import ActionType
from app.domain.models import Money
from app.domain.proposals import PROPOSAL_KEY_PREFIX, ProposedAction, proposal_key
from tests.builders import proposal

DAY = date(2026, 10, 28)


def key(**changes: object) -> str:
    base: dict[str, object] = {
        "action_type": ActionType.IRRIGATION,
        "plot_id": 1,
        "zone_id": 2,
        "local_day": DAY,
        "params": {"volume_mm": 15.0},
    }
    return proposal_key(**{**base, **changes})  # type: ignore[arg-type]


def test_key_has_the_proposal_prefix() -> None:
    assert key().startswith(PROPOSAL_KEY_PREFIX)


def test_equal_numbers_give_equal_keys() -> None:
    assert key(params={"volume_mm": 15}) == key(params={"volume_mm": 15.0})
    assert key(params={"volume_mm": 15.0001}) == key(params={"volume_mm": 15.0})


def test_parameter_order_does_not_matter() -> None:
    assert key(params={"a": 1.0, "b": "x"}) == key(params={"b": "x", "a": 1.0})


@pytest.mark.parametrize(
    "change",
    [
        {"action_type": ActionType.EXTRA_IRRIGATION},
        {"plot_id": 9},
        {"zone_id": 3},
        {"zone_id": None},
        {"local_day": DAY + timedelta(days=1)},
        {"params": {"volume_mm": 10.0}},
        {"params": {"volume_mm": 15.0, "product": "urea"}},
    ],
)
def test_anything_that_changes_the_field_changes_the_key(change: dict[str, object]) -> None:
    assert key(**change) != key()


def test_wording_cost_and_proposer_do_not_change_the_key() -> None:
    first = proposal()
    retry = ProposedAction.create(
        action_type=first.action_type,
        plot_id=first.plot_id,
        zone_id=first.zone_id,
        scheduled_for=first.scheduled_for,
        local_day=first.scheduled_for.date(),
        params={"volume_mm": 15},
        rationale="Different words from a second LLM attempt.",
        proposed_by="agent:irrigation:retry",
        estimated_cost=Money(1_000, "COP"),
    )

    assert retry.proposal_key == first.proposal_key


def test_two_fertilizer_doses_do_not_collide() -> None:
    low = proposal(ActionType.FERTILIZER, {"product": "urea", "n_kg_ha": 40.0})
    high = proposal(ActionType.FERTILIZER, {"product": "urea", "n_kg_ha": 60.0})

    assert low.proposal_key != high.proposal_key


def test_scheduled_for_must_be_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        proposal(scheduled_for=datetime(2026, 10, 28, 6, 0))


def test_boolean_parameters_are_rejected() -> None:
    with pytest.raises(TypeError, match="boolean"):
        key(params={"urgent": True})
