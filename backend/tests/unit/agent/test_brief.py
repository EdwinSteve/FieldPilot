import json
from datetime import UTC, date, datetime

import pytest

from app.agent.brief import (
    Assessment,
    FieldBrief,
    Observation,
    ObservationConflictError,
    ObservationKind,
    ObservationLedger,
    ProposalSummary,
    ZoneAssessment,
)

AT = datetime(2026, 10, 28, 11, 0, tzinfo=UTC)
READING = Observation("reading-7", ObservationKind.SOIL_MOISTURE, 2, 21.0, "%", AT)


def test_a_recorded_observation_can_be_looked_up() -> None:
    ledger = ObservationLedger()

    ledger.add(READING)

    assert ledger.get("reading-7") == READING
    assert ledger.get("reading-8") is None
    assert len(ledger) == 1


def test_reading_the_same_value_twice_is_fine() -> None:
    ledger = ObservationLedger()

    ledger.add(READING)
    ledger.add(READING)

    assert len(ledger) == 1


def test_a_changed_value_under_the_same_id_is_a_bug() -> None:
    ledger = ObservationLedger()
    ledger.add(READING)
    changed = Observation("reading-7", ObservationKind.SOIL_MOISTURE, 2, 31.0, "%", AT)

    with pytest.raises(ObservationConflictError, match="reading-7"):
        ledger.add(changed)
    assert ledger.get("reading-7") == READING


def test_the_brief_serialises_to_json_for_the_next_subagent() -> None:
    brief = FieldBrief(
        plot_id=1,
        day=date(2026, 10, 28),
        assessment=Assessment((ZoneAssessment(2, "dry", 21.0, ("reading-7",)),), "Zone 2 is dry."),
        proposals=(ProposalSummary(5, "irrigation", 2, "execute", "autonomous", "executed"),),
    )

    data = json.loads(brief.to_json())

    assert data["day"] == "2026-10-28"
    assert data["assessment"]["zones"][0] == {
        "zone_id": 2,
        "status": "dry",
        "moisture_pct": 21.0,
        "cited": ["reading-7"],
    }
    assert data["proposals"][0]["task_id"] == 5
