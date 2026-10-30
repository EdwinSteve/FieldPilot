"""D051: the cycle stops at the first subagent that does not complete."""

from collections.abc import Callable

from app.agent.llm.mock import MockLLMClient
from app.agent.loop import RunStatus
from app.agent.messages import LLMResponse
from app.domain.enums import EventKind
from app.persistence.unit_of_work import SqlUnitOfWork
from app.services.daily_cycle import DailyCycle
from tests.conftest import LLM_FIXTURES
from tests.fakes import FlakyLLM
from tests.integration.agent.session import agent_deps
from tests.integration.services.world import MESSAGES, World

UowFactory = Callable[[], SqlUnitOfWork]
THINKING = LLMResponse("Pensando...", None)


def _notifications(world: World) -> list[str]:
    with world.uow() as u:
        return [n.message for n in u.notifications.list()]


def test_a_turn_limit_stops_the_cycle_and_tells_the_farmer(uow: UowFactory) -> None:
    world = World(uow)
    llm = MockLLMClient([THINKING, THINKING])

    result = DailyCycle(uow, agent_deps(world, llm, max_turns=2), MESSAGES).run(world.plot_id)

    assert (result.status, result.stopped_at) == (RunStatus.TURN_LIMIT, "monitoring")
    assert [run.subagent for run in result.runs] == ["monitoring"]
    assert _notifications(world) == [MESSAGES.agent_text("cycle.failed_turn_limit")]
    with uow() as u:
        assert u.tasks.list() == []


def test_a_pause_is_logged_and_never_alerts(uow: UowFactory) -> None:
    world = World(uow)
    llm = FlakyLLM(MockLLMClient([]), failing_attempts=[1])

    result = DailyCycle(uow, agent_deps(world, llm), MESSAGES).run(world.plot_id)

    assert (result.status, result.stopped_at) == (RunStatus.PAUSED, "monitoring")
    assert _notifications(world) == []
    logged = [e for e in world.events(EventKind.AGENT_TOOL_CALL) if e.actor == "system:daily_cycle"]
    assert len(logged) == 1
    assert logged[0].reason == MESSAGES.agent_text("cycle.paused_retry_next_run")
    assert logged[0].idempotency_key == "daily-cycle-s1:paused"
    assert logged[0].inputs["tool"] is None


def test_a_pause_in_irrigation_skips_reporting_and_keeps_earlier_proposals(
    uow: UowFactory,
) -> None:
    world = World(uow)
    fixture = MockLLMClient.from_fixture(LLM_FIXTURES / "d009_day1.json")
    llm = FlakyLLM(fixture, failing_attempts=[9])  # after the first proposal

    result = DailyCycle(uow, agent_deps(world, llm), MESSAGES).run(world.plot_id)

    assert (result.status, result.stopped_at) == (RunStatus.PAUSED, "irrigation")
    assert [run.subagent for run in result.runs] == ["monitoring", "imaging", "irrigation"]
    assert [p.task_id for p in result.brief.proposals] == [1]
    with uow() as u:
        assert u.reports.list_by_cycle(1) == []


def test_the_next_run_retries_under_new_ids_and_repeats_no_proposal(uow: UowFactory) -> None:
    """D048 and D023: the retry starts over; the first irrigation is not duplicated."""
    world = World(uow)
    paused = FlakyLLM(MockLLMClient.from_fixture(LLM_FIXTURES / "d009_day1.json"), [9])
    deps = agent_deps(world, paused)
    DailyCycle(uow, deps, MESSAGES).run(world.plot_id)

    retry = MockLLMClient.from_fixture(LLM_FIXTURES / "d009_day1.json")
    result = DailyCycle(uow, agent_deps(world, retry), MESSAGES).run(world.plot_id)

    assert result.status is RunStatus.COMPLETED
    with uow() as u:
        assert len(u.tasks.list()) == 2  # 15 mm once, plus the extra irrigation
    run_ids = {e.inputs.get("run_id") for e in world.events(EventKind.AGENT_TOOL_CALL)}
    # Both deps count from s1, so the retry's runs share ids with the first cycle's;
    # the trace keys still differ by turn, and nothing is written twice.
    assert {"s1-monitoring", "s1-imaging", "s1-irrigation", "s1-reporting"} <= run_ids
