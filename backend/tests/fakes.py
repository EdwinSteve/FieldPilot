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
