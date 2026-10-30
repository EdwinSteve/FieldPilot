"""D009 end to end on a hand-written fixture: the daily cycle irrigates 15 mm, schedules a
10 mm NOTIFY extra irrigation for the next day, and the farmer reverts it in time.

This checks the business logic of D009. A recording from the real model, which checks
format compatibility, comes in step 11; neither replaces the other.
"""

import json
from collections.abc import Callable
from datetime import timedelta

from app.agent.llm.mock import MockLLMClient
from app.agent.loop import RunStatus
from app.agent.messages import UserMessage
from app.domain.enums import ActionType, EventKind, TaskStatus
from app.persistence.unit_of_work import SqlUnitOfWork
from app.services.daily_cycle import DailyCycle
from app.services.gate_context import local_day, volume_mm
from tests.conftest import LLM_FIXTURES
from tests.integration.agent.session import CATALOGUE, agent_deps
from tests.integration.services.world import DAY1, MESSAGES, World

UowFactory = Callable[[], SqlUnitOfWork]


def _run_day1(uow: UowFactory) -> tuple[World, MockLLMClient]:
    world = World(uow)
    llm = MockLLMClient.from_fixture(LLM_FIXTURES / "d009_day1.json")
    result = DailyCycle(uow, agent_deps(world, llm), MESSAGES).run(world.plot_id)
    assert result.status is RunStatus.COMPLETED, result
    assert [run.subagent for run in result.runs] == [
        "monitoring",
        "imaging",
        "irrigation",
        "reporting",
    ]
    return world, llm


def test_day1_irrigates_and_schedules_the_extra_irrigation(uow: UowFactory) -> None:
    world, _ = _run_day1(uow)

    first, extra = world.task(1), world.task(2)
    assert (first.action_type, first.status, volume_mm(first)) == (
        ActionType.IRRIGATION,
        TaskStatus.EXECUTED,
        15.0,
    )
    assert (extra.action_type, extra.status, volume_mm(extra)) == (
        ActionType.EXTRA_IRRIGATION,
        TaskStatus.SCHEDULED,
        10.0,
    )
    assert extra.scheduled_for == DAY1 + timedelta(days=1)
    assert extra.revert_deadline is not None and extra.revert_deadline > DAY1


def test_the_report_is_saved_and_every_turn_is_traced(uow: UowFactory) -> None:
    world, llm = _run_day1(uow)

    with uow() as u:
        [report] = u.reports.list_by_cycle(1)
    assert report.content.startswith("La zona 2 estaba al 20 % de humedad")
    assert "aproximadamente 25 % de suelo desnudo" in report.content
    trace = world.events(EventKind.AGENT_TOOL_CALL)
    assert len(trace) == len(llm.requests) == 11
    hashes = {agent.name: agent.prompt_sha256 for agent in CATALOGUE}
    for event in trace:
        subagent = event.actor.removeprefix("agent:")
        assert event.inputs["prompt_sha256"] == hashes[subagent]
        assert event.inputs["error"] is None


def test_d009_the_extra_irrigation_is_reverted_before_it_runs(uow: UowFactory) -> None:
    """D009 required test: SCHEDULED while the clock is before scheduled_for; reverted in
    that state; no execution event for it; the first day's total stays at 15 mm."""
    world, _ = _run_day1(uow)
    world.clock.advance(timedelta(hours=1))
    extra = world.task(2)
    assert world.clock.now() < extra.scheduled_for
    assert extra.status is TaskStatus.SCHEDULED

    world.revert.revert(2, "farmer")

    assert world.task(2).status is TaskStatus.REVERTED
    assert world.events(EventKind.EXECUTION, task_id=2) == []
    with uow() as u:
        plot = u.plots.get(world.plot_id)
        day1 = local_day(DAY1, plot)
        tasks = [t for t in u.tasks.list() if t.status is TaskStatus.EXECUTED]
    assert sum(volume_mm(t) for t in tasks if local_day(t.scheduled_for, plot) == day1) == 15.0


def test_each_subagent_receives_the_brief_of_the_ones_before(uow: UowFactory) -> None:
    """D044: handoffs are the structured brief, never free text."""
    _, llm = _run_day1(uow)
    tasks = {
        request.instructions: request.messages[0]
        for request in llm.requests
        if request.messages and isinstance(request.messages[0], UserMessage)
    }
    by_agent = {
        agent.name: tasks[agent.system_prompt]
        for agent in CATALOGUE
        if agent.system_prompt in tasks
    }

    irrigation = by_agent["irrigation"]
    reporting = by_agent["reporting"]
    assert isinstance(irrigation, UserMessage) and isinstance(reporting, UserMessage)
    irrigation_brief = json.loads(irrigation.text.split("Brief: ", 1)[1])
    reporting_brief = json.loads(reporting.text.split("Brief: ", 1)[1])
    assert irrigation_brief["assessment"]["zones"][0]["status"] == "dry"
    assert irrigation_brief["imaging"]["scene_id"] == "neiva-2026-10-28"
    assert irrigation_brief["imaging"]["zones"][0]["low_vigor"] is True
    assert reporting_brief["imaging"]["zones"][0]["bare_soil_pct"] == 25.3
    assert irrigation_brief["proposals"] == []
    assert [p["task_id"] for p in reporting_brief["proposals"]] == [1, 2]
