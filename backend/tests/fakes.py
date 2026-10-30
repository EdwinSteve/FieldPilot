"""Test doubles shared across test modules."""

from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta

from app.agent.llm.ports import LLMClient, LLMUnavailableError
from app.agent.messages import LLMResponse, Message, ToolSpec
from app.agent.trace import TraceEntry


class FakeWall:
    """Controllable wall clock. Call it to read the time; `tick` to move it."""

    def __init__(self, start: datetime) -> None:
        self.current = start

    def __call__(self) -> datetime:
        return self.current

    def tick(self, delta: timedelta) -> None:
        self.current += delta


class FakeClock:
    """Simulated time that moves only through `advance` (D016)."""

    def __init__(self, start: datetime) -> None:
        self.current = start

    def now(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


class FakeEmergencyStop:
    """Emergency stop flag a test can flip."""

    def __init__(self, active: bool = False) -> None:
        self.active = active

    def is_active(self) -> bool:
        return self.active


class FakeTimer:
    """Monotonic timer for the agent loop: each read moves 5 ms forward."""

    def __init__(self) -> None:
        self.reads = 0

    def __call__(self) -> float:
        self.reads += 1
        return self.reads * 0.005


class RecordingTrace:
    """Trace sink that keeps entries in memory."""

    def __init__(self) -> None:
        self.entries: list[TraceEntry] = []

    def record(self, entry: TraceEntry) -> None:
        self.entries.append(entry)


class FlakyLLM:
    """Wraps a client and raises `LLMUnavailableError` on the given attempt numbers."""

    def __init__(self, inner: LLMClient, failing_attempts: Iterable[int]) -> None:
        self._inner = inner
        self._failing = set(failing_attempts)
        self.attempts = 0

    def complete(
        self, instructions: str, messages: Sequence[Message], tools: Sequence[ToolSpec]
    ) -> LLMResponse:
        self.attempts += 1
        if self.attempts in self._failing:
            raise LLMUnavailableError("simulated outage")
        return self._inner.complete(instructions, messages, tools)
