"""Use cases for controlling the simulated clock.

Every effective change is saved and logged as a `clock_changed` event in one
transaction. Operations that change nothing write nothing, so the log is not
filled with empty entries.
"""

from collections.abc import Callable
from datetime import datetime, timedelta

from app.domain.enums import EventKind
from app.domain.models import Event, JsonValue, SimClockState
from app.persistence.ports import UnitOfWork
from app.simulator.clock import SimClock, WallClock

UowFactory = Callable[[], UnitOfWork]


def load_or_start_clock(uow: UowFactory, wall: WallClock, default_start: datetime) -> SimClock:
    """Restore the persisted clock, or start a paused one at `default_start`."""
    with uow() as u:
        state = u.sim_clock.get()
        if state is not None:
            return SimClock(state, wall)
        clock = SimClock.start(default_start, wall)
        u.sim_clock.save(clock.state)
        u.commit()
    return clock


class ClockService:
    """Pause, resume, speed up or jump the simulated clock, with an audit trail."""

    def __init__(self, clock: SimClock, uow: UowFactory) -> None:
        self._clock = clock
        self._uow = uow

    def pause(self, actor: str) -> bool:
        return self._apply(actor, "pause", self._clock.pause)

    def resume(self, actor: str) -> bool:
        return self._apply(actor, "resume", self._clock.resume)

    def set_speed(self, actor: str, factor: float) -> bool:
        return self._apply(actor, f"set speed x{factor:g}", lambda: self._clock.set_speed(factor))

    def advance(self, actor: str, delta: timedelta) -> bool:
        return self._apply(actor, f"advance {delta}", lambda: self._clock.advance(delta))

    def _apply(self, actor: str, action: str, change: Callable[[], bool]) -> bool:
        before = self._clock.state
        if not change():
            return False
        after = self._clock.state
        with self._uow() as u:
            u.events.append(
                Event(
                    kind=EventKind.CLOCK_CHANGED,
                    actor=actor,
                    reason=f"Simulated clock: {action}.",
                    occurred_at=self._clock.now(),
                    inputs={
                        "action": action,
                        "before": _describe(before),
                        "after": _describe(after),
                    },
                )
            )
            u.sim_clock.save(after)
            u.commit()
        return True


def _describe(state: SimClockState) -> dict[str, JsonValue]:
    return {
        "sim_time": state.sim_anchor.isoformat(),
        "speed_factor": state.speed_factor,
        "paused": state.paused,
    }
