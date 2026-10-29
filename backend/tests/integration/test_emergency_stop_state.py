from collections.abc import Callable

from app.actuation.emergency import StoredEmergencyStop
from app.domain.enums import EventKind
from app.persistence.unit_of_work import SqlUnitOfWork
from tests.conftest import make_event


def test_reads_the_persisted_flag_at_every_call(uow: Callable[[], SqlUnitOfWork]) -> None:
    flag = StoredEmergencyStop(uow)
    assert flag.is_active() is False

    with uow() as u:
        u.control.set_emergency_stop(True, make_event(EventKind.EMERGENCY_STOP))
        u.commit()

    assert flag.is_active() is True
