"""The emergency stop, switched by a person and always logged (D022)."""

from collections.abc import Callable

from app.domain.enums import EventKind
from app.domain.models import ControlState, Event
from app.persistence.ports import UnitOfWork
from app.simulator.clock import Clock

UowFactory = Callable[[], UnitOfWork]


class EmergencyStopService:
    def __init__(self, uow: UowFactory, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def state(self) -> ControlState:
        with self._uow() as u:
            return u.control.get()

    def set(self, active: bool, actor: str) -> ControlState:
        """Switch the stop. Setting it to what it already is changes and logs nothing."""
        with self._uow() as u:
            current = u.control.get()
            if current.emergency_stop_active == active:
                return current
            verb = "activated" if active else "released"
            state = u.control.set_emergency_stop(
                active,
                Event(
                    kind=EventKind.EMERGENCY_STOP,
                    actor=actor,
                    reason=f"Emergency stop {verb}.",
                    occurred_at=self._clock.now(),
                    inputs={"active": active},
                ),
            )
            u.commit()
        return state
