"""Test doubles shared across test modules."""

from datetime import datetime, timedelta


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
