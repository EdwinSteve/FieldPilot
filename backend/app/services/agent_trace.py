"""Writes the agent trace to the event log: one `agent_tool_call` event per entry (D045)."""

from collections.abc import Callable

from app.agent.trace import TraceEntry
from app.domain.enums import EventKind
from app.domain.models import Event
from app.persistence.ports import UnitOfWork
from app.simulator.clock import Clock

UowFactory = Callable[[], UnitOfWork]


class EventLogTraceSink:
    """Each entry in its own transaction, so progress survives a crash mid-run."""

    def __init__(self, uow: UowFactory, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def record(self, entry: TraceEntry) -> None:
        """Append the entry unless its key is already logged (resume never duplicates)."""
        with self._uow() as u:
            if u.events.find_by_key(EventKind.AGENT_TOOL_CALL, entry.key) is not None:
                return
            u.events.append(trace_event(entry, self._clock))
            u.commit()


def trace_event(entry: TraceEntry, clock: Clock) -> Event:
    return Event(
        kind=EventKind.AGENT_TOOL_CALL,
        actor=f"agent:{entry.subagent}",
        reason=_reason(entry),
        occurred_at=clock.now(),
        inputs={
            "run_id": entry.run_id,
            "subagent": entry.subagent,
            "turn": entry.turn,
            "tool": entry.tool,
            "arguments": entry.arguments,
            "result": None if entry.result is None else dict(entry.result),
            "error": entry.error,
            "duration_ms": entry.duration_ms,
            "usage": {
                "input_tokens": entry.usage.input_tokens,
                "output_tokens": entry.usage.output_tokens,
            },
            "pause": entry.pause,
        },
        idempotency_key=entry.key,
    )


def _reason(entry: TraceEntry) -> str:
    prefix = f"Turn {entry.turn}"
    if entry.pause is not None:
        return f"{prefix}: paused, the model is unavailable ({entry.error})."
    if entry.tool is None:
        return f"{prefix}: answered with text."
    if entry.error is not None:
        return f"{prefix}: {entry.tool} refused: {entry.error}"
    return f"{prefix}: called {entry.tool}."
