from collections.abc import Callable
from datetime import timedelta

import pytest

from app.domain.enums import EventKind
from app.persistence.unit_of_work import SqlUnitOfWork
from app.services.clock import ClockService, load_or_start_clock
from tests.conftest import T0
from tests.fakes import FakeWall

UowFactory = Callable[[], SqlUnitOfWork]


@pytest.fixture
def wall() -> FakeWall:
    return FakeWall(T0)


def clock_events(uow: UowFactory) -> list[str]:
    with uow() as u:
        return [str(e.inputs["action"]) for e in u.events.list(kind=EventKind.CLOCK_CHANGED)]


def test_advance_by_zero_writes_no_event_and_saves_nothing(uow: UowFactory, wall: FakeWall) -> None:
    clock = load_or_start_clock(uow, wall, T0)
    with uow() as u:
        saved_before = u.sim_clock.get()

    changed = ClockService(clock, uow).advance("farmer", timedelta(0))

    assert changed is False
    assert clock_events(uow) == []
    with uow() as u:
        assert u.sim_clock.get() == saved_before


def test_effective_change_is_logged_and_persisted(uow: UowFactory, wall: FakeWall) -> None:
    clock = load_or_start_clock(uow, wall, T0)

    ClockService(clock, uow).advance("demo", timedelta(hours=13))

    with uow() as u:
        [event] = u.events.list(kind=EventKind.CLOCK_CHANGED)
        saved = u.sim_clock.get()
    assert event.actor == "demo"
    assert event.occurred_at == T0 + timedelta(hours=13)
    assert event.inputs["before"] != event.inputs["after"]
    assert saved is not None and saved.sim_anchor == T0 + timedelta(hours=13)


def test_repeated_pause_is_logged_once(uow: UowFactory, wall: FakeWall) -> None:
    clock = load_or_start_clock(uow, wall, T0)
    service = ClockService(clock, uow)

    service.resume("demo")
    service.pause("demo")
    service.pause("demo")

    assert clock_events(uow) == ["resume", "pause"]


def test_restart_restores_the_persisted_clock(uow: UowFactory, wall: FakeWall) -> None:
    clock = load_or_start_clock(uow, wall, T0)
    service = ClockService(clock, uow)
    service.set_speed("demo", 60.0)
    service.resume("demo")
    wall.tick(timedelta(minutes=2))  # +2 h simulated

    restored = load_or_start_clock(uow, wall, default_start=T0 - timedelta(days=30))

    assert restored.now() == T0 + timedelta(hours=2)
    assert restored.paused is False
