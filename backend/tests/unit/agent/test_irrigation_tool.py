import json
from datetime import date, timedelta

import pytest

from app.agent.brief import Assessment, BriefDraft, ObservationLedger, ZoneAssessment
from app.agent.field import ProposalView
from app.agent.toolbox import cycle_registry
from app.agent.tools.field_tools import ReadContext
from app.agent.tools.registry import ToolOutcome, ToolRegistry
from tests.unit.agent.field_fakes import NOW, FakeProposer, FakeReader

ASSESSMENT = Assessment((ZoneAssessment(2, "dry", 21.0, ("reading-412",)),), "Zona 2 seca.")


@pytest.fixture
def proposer() -> FakeProposer:
    return FakeProposer()


@pytest.fixture
def ledger() -> ObservationLedger:
    return ObservationLedger()


@pytest.fixture
def draft() -> BriefDraft:
    draft = BriefDraft(1, date(2026, 10, 28))
    draft.assessment = ASSESSMENT
    return draft


@pytest.fixture
def tools(draft: BriefDraft, proposer: FakeProposer, ledger: ObservationLedger) -> ToolRegistry:
    registry = cycle_registry(ReadContext(1, FakeReader(), ledger, lambda: NOW), draft, proposer)
    registry.call("read_zone", '{"zone_id": 2}')
    return registry


def _propose(tools: ToolRegistry, **overrides: object) -> ToolOutcome:
    args: dict[str, object] = {
        "action_type": "irrigation",
        "zone_id": 2,
        "volume_mm": 15.0,
        "scheduled_for": "now",
        "rationale": "Humedad del 21 % frente a 32 % de capacidad; riego de 15 mm.",
        "cited": ["reading-412", "zone-2-field-capacity"],
    }
    args.update(overrides)
    return tools.call("propose_action", json.dumps(args))


def test_propose_action_is_the_writing_tool_and_finish_closes(tools: ToolRegistry) -> None:
    propose, finish = tools.get("propose_action"), tools.get("finish")

    assert propose is not None and propose.writes and not propose.closes_run
    assert finish is not None and finish.closes_run and not finish.writes


def test_a_valid_proposal_goes_to_the_proposer_and_into_the_brief(
    tools: ToolRegistry, proposer: FakeProposer, draft: BriefDraft, ledger: ObservationLedger
) -> None:
    outcome = _propose(tools)

    assert outcome.error is None
    [request] = proposer.requests
    assert (request.action_type, request.plot_id, request.zone_id) == ("irrigation", 1, 2)
    assert request.scheduled_for == NOW  # "now" is the simulated clock
    assert request.params == {"volume_mm": 15.0}
    assert request.proposed_by == "agent:irrigation"
    assert outcome.result == {
        "task_id": 21,
        "observation_id": "task-21",
        "status": "executed",
        "outcome": "execute",
        "effective_level": "autonomous",
        "reason_es": None,
        "already_decided": False,
    }
    assert [p.task_id for p in draft.proposals] == [21]
    task = ledger.get("task-21")
    assert task is not None and (task.value, task.unit) == (15.0, "mm")


def test_a_held_proposal_returns_the_reason_in_spanish(
    draft: BriefDraft, ledger: ObservationLedger
) -> None:
    held = ProposalView(
        22, "pending_approval", "await_approval", "approval", "Pendiente por lluvia", False
    )
    registry = cycle_registry(
        ReadContext(1, FakeReader(), ledger, lambda: NOW), draft, FakeProposer(held)
    )
    registry.call("read_zone", '{"zone_id": 2}')

    outcome = _propose(registry)

    assert outcome.result is not None and outcome.result["reason_es"] == "Pendiente por lluvia"
    assert draft.proposals[0].outcome == "await_approval"


def test_a_repeated_proposal_of_a_known_task_does_not_conflict(
    draft: BriefDraft, ledger: ObservationLedger
) -> None:
    """read_zone already put task-7 (15 mm) in the ledger; the gate returns task 7 again."""
    seven = FakeProposer(ProposalView(7, "executed", "execute", "autonomous", None, True))
    registry = cycle_registry(ReadContext(1, FakeReader(), ledger, lambda: NOW), draft, seven)
    registry.call("read_zone", '{"zone_id": 2}')

    outcome = _propose(registry, volume_mm=12.0, rationale="Riego de 12 mm.")

    assert outcome.error is None
    assert outcome.result is not None and outcome.result["already_decided"] is True
    task = ledger.get("task-7")
    assert task is not None and task.value == 15.0  # the stored task, not the new wording


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"scheduled_for": (NOW - timedelta(minutes=1)).isoformat()}, "is in the past"),
        ({"volume_mm": None}, "irrigation needs volume_mm"),
        ({"action_type": "stop_irrigation"}, "stop_irrigation takes no volume_mm"),
        ({"zone_id": 9}, "Zone 9 is not in this plot"),
        ({"cited": ["reading-999"]}, "Cited ids you never read: ['reading-999']"),
        (
            {"rationale": "Humedad del 19 %."},
            "Rationale numbers not in any cited observation: ['19 %']",
        ),
    ],
)
def test_malformed_proposals_never_reach_the_gate(
    tools: ToolRegistry, proposer: FakeProposer, overrides: dict[str, object], message: str
) -> None:
    outcome = _propose(tools, **overrides)

    assert outcome.error is not None and message in outcome.error
    assert proposer.requests == []


def test_types_outside_irrigation_are_refused_by_the_schema(
    tools: ToolRegistry, proposer: FakeProposer
) -> None:
    outcome = _propose(tools, action_type="fertilizer")

    assert outcome.error is not None and outcome.error.startswith("Invalid arguments: action_type")
    assert proposer.requests == []


def test_a_naive_time_is_refused_by_the_schema(tools: ToolRegistry, proposer: FakeProposer) -> None:
    outcome = _propose(tools, scheduled_for="2026-10-29T11:00:00")

    assert outcome.error is not None and "scheduled_for" in outcome.error
    assert proposer.requests == []


def test_no_proposal_without_an_assessment(
    proposer: FakeProposer, ledger: ObservationLedger
) -> None:
    registry = cycle_registry(
        ReadContext(1, FakeReader(), ledger, lambda: NOW),
        BriefDraft(1, date(2026, 10, 28)),
        proposer,
    )
    registry.call("read_zone", '{"zone_id": 2}')

    outcome = _propose(registry)

    assert outcome.error is not None and "no submitted assessment" in outcome.error
    assert proposer.requests == []


def test_an_extra_irrigation_for_tomorrow_is_accepted(
    tools: ToolRegistry, proposer: FakeProposer
) -> None:
    tomorrow = (NOW + timedelta(days=1)).isoformat()

    outcome = _propose(
        tools,
        action_type="extra_irrigation",
        volume_mm=10.0,
        scheduled_for=tomorrow,
        rationale="Riego extra de 10 mm mañana.",
    )

    assert outcome.error is None
    assert proposer.requests[0].scheduled_for == NOW + timedelta(days=1)


def test_finish_reports_the_proposals(tools: ToolRegistry) -> None:
    _propose(tools)

    outcome = tools.call("finish", '{"summary": "Riego propuesto en zona 2."}')

    assert outcome.closes_run
    assert outcome.result == {
        "finished": True,
        "summary": "Riego propuesto en zona 2.",
        "proposals": 1,
    }
