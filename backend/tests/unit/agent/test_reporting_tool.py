import json

import pytest

from app.agent.brief import ObservationLedger
from app.agent.tools.field_tools import ReadContext, read_tools
from app.agent.tools.registry import ToolOutcome, ToolRegistry
from app.agent.tools.reporting import reporting_tools
from tests.unit.agent.field_fakes import NOW, FakeOutbox, FakeReader

GOOD_TEXT = "Zona 2 al 21 %; se regaron 15 mm."
GOOD_CITED = ["reading-412", "task-7"]
GOOD_ACTIONS = [{"task_id": 7, "status": "executed"}]


@pytest.fixture
def outbox() -> FakeOutbox:
    return FakeOutbox()


@pytest.fixture
def tools(outbox: FakeOutbox) -> ToolRegistry:
    read = ReadContext(1, FakeReader(), ObservationLedger(), lambda: NOW)
    registry = ToolRegistry([*read_tools(read), *reporting_tools(read, outbox)])
    registry.call("read_zone", '{"zone_id": 2}')
    return registry


def _submit(
    tools: ToolRegistry,
    text: str = GOOD_TEXT,
    cited: list[str] | None = None,
    actions: list[dict[str, object]] | None = None,
) -> ToolOutcome:
    body = {
        "text_es": text,
        "cited": GOOD_CITED if cited is None else cited,
        "actions": GOOD_ACTIONS if actions is None else actions,
    }
    return tools.call("submit_report", json.dumps(body))


def test_a_verified_report_is_saved_and_closes(tools: ToolRegistry, outbox: FakeOutbox) -> None:
    outcome = _submit(tools)

    assert outcome.error is None and outcome.closes_run
    assert outcome.result == {"saved": True, "report_id": 1}
    assert outbox.reports == [GOOD_TEXT]


def test_an_unsupported_number_is_refused(tools: ToolRegistry, outbox: FakeOutbox) -> None:
    outcome = _submit(tools, "Zona 2 al 25 %.")

    assert outcome.error == (
        "Report refused (1 of 3): Numbers not in any cited observation: ['25 %']."
    )
    assert outbox.reports == []


def test_a_wrong_task_status_is_refused(tools: ToolRegistry) -> None:
    outcome = _submit(tools, actions=[{"task_id": 9, "status": "executed"}])

    assert outcome.error is not None
    assert "Task 9 is scheduled, not executed as declared." in outcome.error


def test_a_task_of_another_plot_is_refused(tools: ToolRegistry) -> None:
    outcome = _submit(tools, actions=[{"task_id": 404, "status": "executed"}])

    assert outcome.error is not None and "Task 404 does not exist in this plot." in outcome.error


def test_a_cited_id_never_read_is_refused(tools: ToolRegistry) -> None:
    outcome = _submit(tools, cited=["reading-412", "task-7", "reading-1"])

    assert outcome.error is not None and "Cited ids you never read: ['reading-1']" in outcome.error


def test_the_third_refusal_escalates_and_saves_nothing(
    tools: ToolRegistry, outbox: FakeOutbox
) -> None:
    """D052: the loop stops; the verification does not."""
    first = _submit(tools, "Zona 2 al 25 %.")
    second = _submit(tools, "Zona 2 al 26 %.")
    third = _submit(tools, "Zona 2 al 27 %.")

    assert first.error is not None and "(1 of 3)" in first.error
    assert second.error is not None and "(2 of 3)" in second.error
    assert third.error is None and third.closes_run
    assert third.result == {
        "escalated": True,
        "saved": False,
        "refusals": 3,
        "problems": ["Numbers not in any cited observation: ['27 %']."],
    }
    assert outbox.reports == []
    assert outbox.notifications == ["report.escalated_unverified"]


def test_a_good_report_after_two_refusals_is_saved(tools: ToolRegistry, outbox: FakeOutbox) -> None:
    _submit(tools, "Zona 2 al 25 %.")
    _submit(tools, "Zona 2 al 26 %.")

    outcome = _submit(tools)

    assert outcome.result == {"saved": True, "report_id": 1}
    assert outbox.notifications == []


def test_schema_errors_do_not_count_as_check_refusals(
    tools: ToolRegistry, outbox: FakeOutbox
) -> None:
    for _ in range(3):
        tools.call("submit_report", '{"text_es": "Hola"}')

    outcome = _submit(tools, "Zona 2 al 25 %.")

    assert outcome.error is not None and "(1 of 3)" in outcome.error
    assert outbox.notifications == []
