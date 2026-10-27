"""Clock interface and the accelerated simulation clock.

`SimClock` is pure: it does no I/O and receives wall time as an injected
function, so tests control time completely. Persistence of its state and
logging of its changes live in `app.services.clock`.
"""

import math
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.domain.models import SimClockState

WallClock = Callable[[], datetime]


def system_wall_clock() -> datetime:
    """Current wall time, timezone-aware UTC."""
    return datetime.now(UTC)


class Clock(Protocol):
    """Source of the current time for domain code. Always aware UTC."""

    def now(self) -> datetime: ...


class SimClock:
    """Simulated time: `sim_anchor + (wall - wall_anchor) * speed`, or frozen while paused.

    Every operation re-anchors first, so `now()` is continuous across
    pause, resume and speed changes, and never moves backwards. Each
    mutator returns True only if it changed something.
    """

    def __init__(self, state: SimClockState, wall: WallClock) -> None:
        _ensure_aware(state.sim_anchor, "sim_anchor")
        _ensure_aware(state.wall_anchor, "wall_anchor")
        _ensure_valid_speed(state.speed_factor)
        self._state = state
        self._wall = wall
        self._last_now = state.sim_anchor

    @classmethod
    def start(
        cls,
        sim_start: datetime,
        wall: WallClock,
        speed_factor: float = 1.0,
        paused: bool = True,
    ) -> "SimClock":
        """Create a clock that starts at `sim_start` now."""
        state = SimClockState(
            sim_anchor=sim_start, wall_anchor=wall(), speed_factor=speed_factor, paused=paused
        )
        return cls(state, wall)

    @property
    def state(self) -> SimClockState:
        """Current anchors, re-based on the present so they can be persisted."""
        return self._reanchored()

    @property
    def paused(self) -> bool:
        return self._state.paused

    @property
    def speed_factor(self) -> float:
        return self._state.speed_factor

    def now(self) -> datetime:
        """Current simulated time."""
        candidate = self._compute_now()
        # Guard against a wall clock that steps backwards (NTP, suspend).
        self._last_now = max(self._last_now, candidate)
        return self._last_now

    def pause(self) -> bool:
        if self._state.paused:
            return False
        self._state = replace(self._reanchored(), paused=True)
        return True

    def resume(self) -> bool:
        if not self._state.paused:
            return False
        self._state = replace(self._reanchored(), paused=False)
        return True

    def set_speed(self, factor: float) -> bool:
        _ensure_valid_speed(factor)
        if factor == self._state.speed_factor:
            return False
        self._state = replace(self._reanchored(), speed_factor=factor)
        return True

    def advance(self, delta: timedelta) -> bool:
        """Jump simulated time forward by `delta`, paused or not."""
        if delta < timedelta(0):
            raise ValueError("the simulated clock never moves backwards")
        if delta == timedelta(0):
            return False
        anchored = self._reanchored()
        self._state = replace(anchored, sim_anchor=anchored.sim_anchor + delta)
        self._last_now = self._state.sim_anchor
        return True

    def _compute_now(self) -> datetime:
        if self._state.paused:
            return self._state.sim_anchor
        elapsed = max(self._wall() - self._state.wall_anchor, timedelta(0))
        return self._state.sim_anchor + elapsed * self._state.speed_factor

    def _reanchored(self) -> SimClockState:
        """State with anchors moved to the present, so later changes start from here."""
        return replace(self._state, sim_anchor=self.now(), wall_anchor=self._wall())


def _ensure_aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _ensure_valid_speed(factor: float) -> None:
    if not math.isfinite(factor) or factor <= 0:
        raise ValueError(f"speed factor must be a positive finite number, got {factor}")
