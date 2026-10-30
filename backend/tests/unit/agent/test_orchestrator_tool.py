import json

from app.agent.brief import ObservationLedger
from app.agent.tools.field_tools import ReadContext, read_tools
from app.agent.tools.orchestrator import orchestrator_tools
from app.agent.tools.registry import ToolRegistry
from tests.unit.agent.field_fakes import NOW, FakeReader


def _tools() -> ToolRegistry:
    read = ReadContext(1, FakeReader(), ObservationLedger(), lambda: NOW)
    registry = ToolRegistry([*read_tools(read), *orchestrator_tools(read)])
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
