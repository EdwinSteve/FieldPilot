import json
from datetime import date

from app.agent.brief import Assessment, BriefDraft, ObservationLedger, ZoneAssessment
from app.agent.loop import AgentRun, RunStatus
from app.agent.tools.field_tools import ReadContext, read_tools
from app.agent.tools.orchestrator import Consultant, orchestrator_tools
from app.agent.tools.registry import ToolRegistry
from tests.unit.agent.field_fakes import NOW, FakeReader, NoConsultant


def _tools(draft: BriefDraft | None = None, consultant: Consultant | None = None) -> ToolRegistry:
    draft = draft or BriefDraft(1, date(2026, 10, 28))
    consultant = consultant or NoConsultant()
    read = ReadContext(1, FakeReader(), ObservationLedger(), lambda: NOW)
    registry = ToolRegistry([*read_tools(read), *orchestrator_tools(read, draft, consultant)])
    registry.call("read_zone", '{"zone_id": 2}')
    return registry


def test_a_supported_answer_closes_with_the_text() -> None:
    body = {"text_es": "La zona 2 está al 21 %.", "cited": ["reading-412"]}

    outcome = _tools().call("answer_farmer", json.dumps(body))

    assert outcome.closes_run and outcome.result == {"answer": "La zona 2 está al 21 %."}


def test_an_unsupported_number_is_refused() -> None:
    """D053: the chat answer passes the same check as a report."""
    body = {"text_es": "La zona 2 está al 30 %.", "cited": ["reading-412"]}

    outcome = _tools().call("answer_farmer", json.dumps(body))

    assert outcome.error == "Answer refused: Numbers not in any cited observation: ['30 %']."
    assert not outcome.closes_run


def test_an_uncited_number_is_refused_even_if_it_was_read() -> None:
    body = {"text_es": "La zona 2 está al 21 %.", "cited": []}

    outcome = _tools().call("answer_farmer", json.dumps(body))

    assert outcome.error is not None and "['21 %']" in outcome.error


def test_a_cited_id_never_read_is_refused() -> None:
    body = {"text_es": "Todo bien.", "cited": ["reading-9"]}

    outcome = _tools().call("answer_farmer", json.dumps(body))

    assert outcome.error == "Answer refused: Cited ids you never read: ['reading-9']."


class FakeConsultant:
    """Monitoring that fills the brief (or not), and records the question."""

    def __init__(self, draft: BriefDraft, completes: bool = True) -> None:
        self.draft = draft
        self.completes = completes
        self.asked: list[tuple[str, str]] = []

    def consult(self, subagent: str, task: str) -> AgentRun:
        self.asked.append((subagent, task))
        status = RunStatus.COMPLETED if self.completes else RunStatus.TURN_LIMIT
        if self.completes:
            self.draft.assessment = Assessment(
                (ZoneAssessment(2, "dry", 21.0, ("reading-412",)),), "Zona 2 seca."
            )
        return AgentRun("r1", subagent, status, None, (), 1)


def test_consult_monitoring_returns_the_verified_brief() -> None:
    draft = BriefDraft(1, date(2026, 10, 28))
    consultant = FakeConsultant(draft)

    outcome = _tools(draft, consultant).call("consult_monitoring", '{"question": "¿Riego?"}')

    assert consultant.asked == [("monitoring", "¿Riego?")]
    assert outcome.result is not None and outcome.result["status"] == "completed"
    brief = outcome.result["brief"]
    assert isinstance(brief, str) and json.loads(brief)["assessment"]["zones"][0]["zone_id"] == 2


def test_consult_monitoring_without_an_assessment_is_an_error() -> None:
    draft = BriefDraft(1, date(2026, 10, 28))

    outcome = _tools(draft, FakeConsultant(draft, completes=False)).call(
        "consult_monitoring", '{"question": "¿Riego?"}'
    )

    assert outcome.error == "Monitoring did not finish its assessment (turn_limit)."


def test_the_chat_has_no_way_to_propose() -> None:
    """D057: no consult_irrigation and no propose_action in the orchestrator's tools."""
    names = {
        t.name
        for t in orchestrator_tools(
            ReadContext(1, FakeReader(), ObservationLedger(), lambda: NOW),
            BriefDraft(1, date(2026, 10, 28)),
            NoConsultant(),
        )
    }

    assert names == {"consult_monitoring", "answer_farmer"}
