"""Emergency stop flag read from the persisted `ControlState`."""

from collections.abc import Callable

from app.persistence.ports import UnitOfWork

UowFactory = Callable[[], UnitOfWork]


class StoredEmergencyStop:
    """Reads the flag at every call, so a stop set elsewhere takes effect at once."""

    def __init__(self, uow: UowFactory) -> None:
        self._uow = uow

    def is_active(self) -> bool:
        with self._uow() as u:
            return u.control.get().emergency_stop_active
