"""D093: the agronomist's data, its task tools and the rules that keep them honest."""

import json
from collections.abc import Callable
from dataclasses import replace
from datetime import timedelta

import pytest

from app.agent.brief import BriefDraft, ObservationLedger, ZoneNutrition
from app.agent.field import TaskNotCancellableError
from app.agent.llm.mock import MockLLMClient
from app.agent.loop import AgentRun, RunStatus
from app.agent.toolbox import cycle_registry
from app.agent.tools.field_tools import ReadContext
from app.agent.tools.registry import ToolRegistry
from app.domain.enums import ActionType, EventKind, SensorKind, TaskStatus
from app.domain.models import Reading, Sensor
from app.persistence.unit_of_work import SqlUnitOfWork
from app.services.agent_outbox import StoredOutbox
from app.services.agent_proposals import GateProposer
from app.services.agent_session import AgentSession
from app.services.agronomy import StoredAgronomy, load_soil_probe, summarize
from app.services.approvals import ApprovalService
from app.services.field_reader import StoredFieldReader
from tests.conftest import CONFIG_DIR
from tests.fakes import FlakyLLM
from tests.integration.agent.session import agent_deps
from tests.integration.services.world import CROPS, MESSAGES, World
from tests.unit.agent.agents import tool

UowFactory = Callable[[], SqlUnitOfWork]
PROBE = load_soil_probe(CONFIG_DIR / "soil_probe.yaml")
HOUR = timedelta(hours=1)


def _agronomy(world: World) -> StoredAgronomy:
    return StoredAgronomy(world.uow, world.clock, PROBE, sites=None)


def _scheduled_irrigation(world: World, proposed_by: str = "agent:irrigation") -> int:
    action = replace(world.action(at=world.clock.now() + 3 * HOUR), proposed_by=proposed_by)
    task = world.proposals.propose(action).task
    assert task.id is not None and task.status is TaskStatus.SCHEDULED
    return task.id


def _tools(world: World, draft: BriefDraft) -> tuple[ToolRegistry, ObservationLedger]:
    deps = agent_deps(world, MockLLMClient([]))
    ledger = ObservationLedger()
    reader = StoredFieldReader(world.uow, world.forecast, CROPS, world.clock)
    read = ReadContext(world.plot_id, reader, ledger, world.clock.now)
    registry = cycle_registry(
        read,
        draft,
        GateProposer(world.uow, world.proposals, MESSAGES),
        StoredOutbox(world.uow, world.clock, MESSAGES),
        _NoConsultant(),
        deps.imagery,
        _agronomy(world),
    )
    return registry, ledger


class _NoConsultant:
    def consult(self, subagent: str, task: str) -> AgentRun:
        raise AssertionError("no consult in these tests")


# --- cancelling -----------------------------------------------------------------------------


def test_an_agent_cancels_its_own_task_and_the_log_says_why(uow: UowFactory) -> None:
    world = World(uow)
    task_id = _scheduled_irrigation(world)

    record = _agronomy(world).cancel(world.plot_id, task_id, "Rain is coming.", "agent:agronomist")

    assert record.status == "cancelled"
    [event] = world.events(EventKind.TASK_CANCELLED, task_id)
    assert (event.actor, event.reason) == ("agent:agronomist", "Rain is coming.")
    assert event.inputs["previous_status"] == "scheduled"
    assert world.task(task_id).status is TaskStatus.CANCELLED


def test_an_agent_never_cancels_the_farmers_task_nor_a_closed_one(uow: UowFactory) -> None:
    world = World(uow)
    farmers = _scheduled_irrigation(world, proposed_by="farmer:1")
    agronomy = _agronomy(world)
    with pytest.raises(TaskNotCancellableError, match="only an agent's task"):
        agronomy.cancel(world.plot_id, farmers, "No.", "agent:agronomist")

    own = _scheduled_irrigation(replace_clock(world))
    agronomy.cancel(world.plot_id, own, "First.", "agent:agronomist")
    with pytest.raises(TaskNotCancellableError, match="cannot be cancelled"):
        agronomy.cancel(world.plot_id, own, "Again.", "agent:agronomist")
    with pytest.raises(TaskNotCancellableError, match="not in this plot"):
        agronomy.cancel(world.plot_id, 999, "Unknown.", "agent:agronomist")


def replace_clock(world: World) -> World:
    """A day later, so the next proposal is a different one (D023)."""
    world.clock.advance(timedelta(days=1))
    return world


# --- soil -----------------------------------------------------------------------------------


def test_the_crop_takes_nitrogen_as_degree_days_accumulate(uow: UowFactory) -> None:
    world = World(uow)
    agronomy = _agronomy(world)
    at_sowing = agronomy.soil(world.plot_id, world.zone_id, world.clock.now())
    with uow() as u:
        [cycle] = u.cycles.list_by_plot(world.plot_id)
        u.cycles.update(replace(cycle, accumulated_gdd=500.0))
        u.commit()

    later = agronomy.soil(world.plot_id, world.zone_id, world.clock.now())

    assert at_sowing is not None and later is not None
    assert at_sowing.nitrogen_ppm == PROBE.zone(0).nitrogen_ppm
    assert later.nitrogen_ppm == pytest.approx(at_sowing.nitrogen_ppm - 1.2 * 5)
    assert (later.ph_source, later.simulated) == ("probe", True)
    assert later.targets["nitrogen"].low == 25  # maize


def test_an_approved_fertilizer_raises_the_nutrient_it_carries(uow: UowFactory) -> None:
    world = World(uow)
    agronomy = _agronomy(world)
    before = agronomy.soil(world.plot_id, world.zone_id, world.clock.now())
    fertilizer = world.action(ActionType.FERTILIZER, params={"product": "Urea 46-0-0",
                                                             "dose_kg_ha": 50.0})  # fmt: skip
    task = world.proposals.propose(fertilizer).task
    assert task.status is TaskStatus.PENDING_APPROVAL  # D005: always the farmer's call
    pending = agronomy.soil(world.plot_id, world.zone_id, world.clock.now())
    ApprovalService(uow, world.clock, world.due).approve(task.id or 0, "farmer:1")

    after = agronomy.soil(world.plot_id, world.zone_id, world.clock.now())

    assert before is not None and pending is not None and after is not None
    assert pending.nitrogen_ppm == before.nitrogen_ppm  # not until the farmer says yes
    assert after.nitrogen_ppm == pytest.approx(before.nitrogen_ppm + 50 * 0.46 * 0.38)
    assert after.phosphorus_ppm == before.phosphorus_ppm


def test_the_farmer_marks_a_manual_task_done(uow: UowFactory) -> None:
    world = World(uow)
    task = world.proposals.propose(world.action(ActionType.SCOUTING_VISIT, params={})).task
    assert task.status is TaskStatus.SCHEDULED  # notify: no actuator, so it waits for a person
    approvals = ApprovalService(uow, world.clock, world.due)

    done = approvals.mark_done(task.id or 0, "farmer:1")

    assert done.status is TaskStatus.EXECUTED
    [event] = world.events(EventKind.EXECUTION, task.id)
    assert event.inputs["manual"] is True and event.actor == "farmer:1"


# --- microclimate ---------------------------------------------------------------------------


def test_humid_leaf_hours_count_only_humid_and_mild_readings(uow: UowFactory) -> None:
    world = World(uow)
    start = world.clock.now() - 4 * HOUR
    with uow() as u:
        t = u.sensors.add(Sensor(world.zone_id, SensorKind.TEMPERATURE, "°C"))
        h = u.sensors.add(Sensor(world.zone_id, SensorKind.HUMIDITY, "%"))
        assert t.id is not None and h.id is not None
        # 4 hourly readings: humid and mild, humid and mild, dry, humid but too hot.
        values = [(20.0, 95.0), (18.0, 92.0), (25.0, 60.0), (33.0, 95.0)]
        u.readings.add_many([Reading(t.id, temp, start + n * HOUR) for n, (temp, _) in
                             enumerate(values)])  # fmt: skip
        u.readings.add_many([Reading(h.id, rh, start + n * HOUR) for n, (_, rh) in
                             enumerate(values)])  # fmt: skip
        u.commit()

    air = _agronomy(world).microclimate(world.plot_id, world.zone_id, world.clock.now())

    assert air is not None and air.readings == 4
    assert air.humid_leaf_hours == pytest.approx(2.0)
    assert air.humidity_max_pct == 95.0 and air.temperature_max_c == 33.0


def test_a_zone_without_air_sensors_has_nothing_to_say(uow: UowFactory) -> None:
    air = summarize(1, (), (), World(uow).clock.now())

    assert air.readings == 0 and air.humid_leaf_hours is None


# --- the agronomist's tools -----------------------------------------------------------------


def test_a_fertilizer_needs_the_soil_nutrition_first(uow: UowFactory) -> None:
    world = World(uow)
    registry, _ = _tools(world, BriefDraft(world.plot_id, world.clock.now().date()))
    arguments = {"action_type": "fertilizer", "zone_id": world.zone_id, "scheduled_for": "now",
                 "product": "urea", "dose_kg_ha": 50, "rationale": "Short of nitrogen.",
                 "cited": ["x"]}  # fmt: skip

    outcome = registry.call("propose_task", json.dumps(arguments))

    assert outcome.error is not None and "consult_soil_nutrition first" in outcome.error
    with uow() as u:
        assert u.tasks.list() == []


def test_editing_a_task_proposes_the_new_one_then_cancels_the_old(uow: UowFactory) -> None:
    world = World(uow)
    old = _scheduled_irrigation(world)  # an agent's open task
    draft = BriefDraft(world.plot_id, world.clock.now().date())
    registry, _ = _tools(world, draft)
    soil = json.loads(registry.call("read_soil", json.dumps({"zone_id": world.zone_id}))
                      .output_json())  # fmt: skip
    nitrogen = soil["nitrogen"]["observation_id"]
    draft.nutrition = (ZoneNutrition(world.zone_id, "low", ("nitrogen",), "Short.", (nitrogen,)),)
    arguments = {"action_type": "fertilizer", "zone_id": world.zone_id, "scheduled_for": "now",
                 "product": "urea", "dose_kg_ha": 40, "rationale": "40 kg/ha of urea instead.",
                 "cited": [nitrogen], "replaces_task_id": old}  # fmt: skip

    result = json.loads(registry.call("propose_task", json.dumps(arguments)).output_json())

    assert result["status"] == "pending_approval"
    assert result["replaced"] == {"task_id": old, "status": "cancelled"}
    assert world.task(old).status is TaskStatus.CANCELLED
    assert draft.cancelled == [old]


def test_the_day_does_not_close_without_the_assessment_and_the_report(uow: UowFactory) -> None:
    world = World(uow)
    registry, _ = _tools(world, BriefDraft(world.plot_id, world.clock.now().date()))

    outcome = registry.call("close_day", json.dumps({"summary": "Done."}))

    assert outcome.error is not None
    assert "consult_monitoring" in outcome.error and "consult_reporting" in outcome.error


# --- a dropped call inside a consult ---------------------------------------------------------


def test_a_consult_resumes_a_dropped_call_instead_of_losing_the_specialist(
    uow: UowFactory,
) -> None:
    """D046, D093: the specialist continues from its transcript; nothing is asked twice."""
    world = World(uow)
    script = MockLLMClient([
        tool("list_zones", "c1"),
        tool("read_zone", "c2", zone_id=world.zone_id),
        tool("submit_assessment", "c3", zones=[{"zone_id": world.zone_id, "status": "dry",
             "moisture_pct": 20.0, "cited": ["reading-1", f"zone-{world.zone_id}-field-capacity"]}],
             summary="The zone is dry."),
    ])  # fmt: skip
    flaky = FlakyLLM(script, failing_attempts=[2])  # the second call drops
    session = AgentSession(agent_deps(world, flaky), world.plot_id, world.clock.now().date())

    run = session.consult("monitoring", "Assess every zone.")

    assert run.status is RunStatus.COMPLETED
    assert session.draft.assessment is not None
    assert [r.status for r in session.runs] == [RunStatus.COMPLETED]  # one run, resumed
    assert len(script.requests) == 3  # every recorded answer used once, in order
