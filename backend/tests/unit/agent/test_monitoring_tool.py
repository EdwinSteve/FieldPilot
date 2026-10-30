import json
from datetime import date

import pytest

from app.agent.brief import BriefDraft, ObservationLedger
from app.agent.toolbox import cycle_registry
from app.agent.tools.field_tools import ReadContext
from app.agent.tools.registry import ToolOutcome, ToolRegistry
from tests.unit.agent.field_fakes import NOW, FakeProposer, FakeReader


@pytest.fixture
def draft() -> BriefDraft:
    return BriefDraft(1, date(2026, 10, 28))


@pytest.fixture
def tools(draft: BriefDraft) -> ToolRegistry:
    registry = cycle_registry(
        ReadContext(1, FakeReader(), ObservationLedger(), lambda: NOW), draft, FakeProposer()
    )
    for zone in (2, 3):
        registry.call("read_zone", json.dumps({"zone_id": zone}))
    registry.call("read_forecast", "{}")
    return registry


def _zone(
    zone_id: int, status: str = "dry", moisture: float | None = 21.0, cited: list[str] | None = None
) -> dict[str, object]:
    default = ["reading-412"] if zone_id == 2 else ["zone-3-field-capacity"]
    return {
        "zone_id": zone_id,
        "status": status,
        "moisture_pct": moisture,
        "cited": cited or default,
    }


GOOD = [_zone(2), _zone(3, "ok", None)]


def _submit(
    tools: ToolRegistry, zones: list[dict[str, object]], summary: str = "Zona 2 seca."
) -> ToolOutcome:
    return tools.call("submit_assessment", json.dumps({"zones": zones, "summary": summary}))


def test_a_correct_assessment_closes_the_run_and_fills_the_brief(
    tools: ToolRegistry, draft: BriefDraft
) -> None:
    cited = ["reading-412", "zone-2-field-capacity", "forecast-plot-1-2026-10-28T11:00Z"]
    zones = [_zone(2, cited=cited), GOOD[1]]

    outcome = _submit(tools, zones, "Zona 2 al 21 % frente a 32 % de capacidad; sin lluvia (0 mm).")

    assert outcome.error is None and outcome.closes_run
    assert draft.assessment is not None
    assert [(z.zone_id, z.status, z.moisture_pct) for z in draft.assessment.zones] == [
        (2, "dry", 21.0),
        (3, "ok", None),
    ]


def test_a_missing_zone_is_refused(tools: ToolRegistry, draft: BriefDraft) -> None:
    outcome = _submit(tools, [_zone(2)])

    assert outcome.error is not None and "missing [3]" in outcome.error
    assert draft.assessment is None


def test_a_repeated_zone_is_refused(tools: ToolRegistry) -> None:
    outcome = _submit(tools, [*GOOD, _zone(2)])

    assert outcome.error is not None and "repeated [2]" in outcome.error


def test_a_zone_outside_the_plot_is_refused(tools: ToolRegistry) -> None:
    outcome = _submit(tools, [*GOOD, _zone(9, cited=["reading-412"])])

    assert outcome.error is not None and "not in the plot [9]" in outcome.error


def test_an_id_never_read_is_refused(tools: ToolRegistry) -> None:
    outcome = _submit(tools, [_zone(2, cited=["reading-999"]), GOOD[1]])

    assert (
        outcome.error is not None and "cited ids you never read: ['reading-999']" in outcome.error
    )


def test_citing_another_zone_is_refused(tools: ToolRegistry) -> None:
    outcome = _submit(tools, [GOOD[0], _zone(3, "ok", None, cited=["reading-412"])])

    assert outcome.error is not None
    assert "Zone 3: cited observations of another zone: ['reading-412']" in outcome.error


def test_a_moisture_that_differs_from_the_reading_is_refused(tools: ToolRegistry) -> None:
    outcome = _submit(tools, [_zone(2, moisture=24.0), GOOD[1]])

    assert outcome.error is not None
    assert "moisture_pct 24.0 matches no cited reading ([21.0])" in outcome.error


def test_a_moisture_without_a_cited_reading_is_refused(tools: ToolRegistry) -> None:
    outcome = _submit(tools, [_zone(2, cited=["zone-2-field-capacity"]), GOOD[1]])

    assert outcome.error is not None and "needs a cited soil moisture reading" in outcome.error


def test_a_summary_number_nobody_read_is_refused(tools: ToolRegistry, draft: BriefDraft) -> None:
    outcome = _submit(tools, GOOD, "Zona 2 al 18 %.")

    assert outcome.error is not None
    assert "Summary numbers not in any cited observation: ['18 %']" in outcome.error
    assert draft.assessment is None


def test_every_problem_is_reported_at_once(tools: ToolRegistry) -> None:
    outcome = _submit(tools, [_zone(2, moisture=30.0)], "Zona 2 al 30 %.")

    assert outcome.error is not None
    assert outcome.error.startswith("Assessment refused: ")
    assert "missing [3]" in outcome.error and "moisture_pct 30.0" in outcome.error
    assert "['30 %']" in outcome.error
