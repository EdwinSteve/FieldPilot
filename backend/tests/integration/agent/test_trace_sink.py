"""The agent trace in the real event log (D045, D048)."""

from collections.abc import Callable
from dataclasses import replace

from app.agent.llm.mock import MockLLMClient
from app.agent.loop import AgentLoop, RunStatus
from app.agent.messages import TokenUsage
from app.agent.trace import TraceEntry
from app.domain.enums import EventKind
from app.domain.models import Event
from app.persistence.unit_of_work import SqlUnitOfWork
from app.services.agent_trace import EventLogTraceSink
from tests.conftest import T0
from tests.fakes import FakeClock, FlakyLLM
from tests.unit.agent.agents import MONITORING, READ, SUBMIT, Calls, make_loop, make_registry

UowFactory = Callable[[], SqlUnitOfWork]


def _trace_events(uow: UowFactory) -> list[Event]:
    with uow() as u:
        return list(u.events.list(kind=EventKind.AGENT_TOOL_CALL))


def test_an_entry_becomes_one_agent_tool_call_event(uow: UowFactory) -> None:
    sink = EventLogTraceSink(uow, FakeClock(T0))

    sink.record(
        TraceEntry(
            "r1",
            "monitoring",
            1,
            "read_moisture",
            {"zone_id": 2},
            {"moisture_pct": 21.0},
            duration_ms=5,
            usage=TokenUsage(120, 14),
        )
    )

    [event] = _trace_events(uow)
    assert event.actor == "agent:monitoring"
    assert event.reason == "Turn 1: called read_moisture."
    assert event.occurred_at == T0
    assert event.idempotency_key == "agent-run-r1:turn-1"
    assert event.inputs == {
        "run_id": "r1",
        "subagent": "monitoring",
        "turn": 1,
        "tool": "read_moisture",
        "arguments": {"zone_id": 2},
        "result": {"moisture_pct": 21.0},
        "error": None,
        "duration_ms": 5,
        "usage": {"input_tokens": 120, "output_tokens": 14},
        "pause": None,
        "prompt_sha256": "",
    }


def test_recording_the_same_entry_twice_writes_it_once(uow: UowFactory) -> None:
    sink = EventLogTraceSink(uow, FakeClock(T0))
    entry = TraceEntry("r1", "monitoring", 1, None, result={"text": "hm"})

    sink.record(entry)
    sink.record(entry)

    assert len(_trace_events(uow)) == 1


def test_reasons_tell_refusals_text_and_pauses_apart(uow: UowFactory) -> None:
    sink = EventLogTraceSink(uow, FakeClock(T0))
    sink.record(TraceEntry("r1", "m", 1, "submit_assessment", {}, error="Bad value."))
    sink.record(TraceEntry("r1", "m", 2, None, result={"text": "hm"}))
    sink.record(TraceEntry("r1", "m", 3, None, error="LLMUnavailableError", pause=1))

    assert [e.reason for e in _trace_events(uow)] == [
        "Turn 1: submit_assessment refused: Bad value.",
        "Turn 2: answered with text.",
        "Turn 3: paused, the model is unavailable (LLMUnavailableError).",
    ]


def test_resuming_twice_records_each_turn_once(uow: UowFactory) -> None:
    """Observation 4: two pauses and two resumes never duplicate a turn."""
    calls = Calls()
    sink = EventLogTraceSink(uow, FakeClock(T0))
    llm = FlakyLLM(MockLLMClient([READ, SUBMIT]), failing_attempts=[2, 3])
    loop = make_loop(llm, calls, sink)

    first = loop.run("monitoring", "Assess zone 2.", "r1")
    second = loop.resume(first)
    done = loop.resume(second)

    assert [first.status, second.status, done.status] == [
        RunStatus.PAUSED,
        RunStatus.PAUSED,
        RunStatus.COMPLETED,
    ]
    keys = [e.idempotency_key for e in _trace_events(uow)]
    assert keys == [
        "agent-run-r1:turn-1",
        "agent-run-r1:turn-2:pause-1",
        "agent-run-r1:turn-2:pause-2",
        "agent-run-r1:turn-2",
    ]
    assert len(keys) == len(set(keys))
    assert calls.read_moisture == 1 and calls.submitted == 1


def test_every_entry_names_the_prompt_version(uow: UowFactory) -> None:
    """D055: the trace ties each turn to the prompt file that produced it."""
    sink = EventLogTraceSink(uow, FakeClock(T0))
    agent = replace(MONITORING, prompt_sha256="ab" * 32)
    llm = FlakyLLM(MockLLMClient([READ, SUBMIT]), failing_attempts=[2])
    loop = AgentLoop(llm, make_registry(Calls()), sink, [agent], max_turns=6)

    loop.resume(loop.run("monitoring", "Assess.", "r1"))

    hashes = {e.inputs["prompt_sha256"] for e in _trace_events(uow)}
    assert hashes == {"ab" * 32}
    assert len(_trace_events(uow)) == 3  # a turn, a pause and the closing turn
