"""The trace port: one entry per turn or paused attempt (D045, D048)."""

from dataclasses import dataclass, field
from typing import Protocol

from app.agent.messages import TokenUsage
from app.domain.models import JsonObject, JsonValue


@dataclass(frozen=True)
class TraceEntry:
    run_id: str
    subagent: str
    turn: int  # the turn completed, or the turn a paused attempt was trying
    tool: str | None  # None for a text answer or a paused attempt
    arguments: JsonValue = None
    result: JsonObject | None = None
    error: str | None = None
    duration_ms: int = 0
    usage: TokenUsage = field(default_factory=TokenUsage)
    pause: int | None = None  # k for the k-th pause of the run; None for a completed turn

    @property
    def key(self) -> str:
        """Idempotency key: resuming a run never records a turn twice."""
        base = f"agent-run-{self.run_id}:turn-{self.turn}"
        return base if self.pause is None else f"{base}:pause-{self.pause}"


class TraceSink(Protocol):
    def record(self, entry: TraceEntry) -> None: ...
