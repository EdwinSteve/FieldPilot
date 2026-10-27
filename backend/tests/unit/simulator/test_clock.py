import math
from datetime import UTC, datetime, timedelta

import pytest

from app.simulator.clock import SimClock
from tests.fakes import FakeWall

SIM_START = datetime(2026, 10, 27, 6, 0, tzinfo=UTC)
WALL_START = datetime(2030, 1, 1, tzinfo=UTC)


@pytest.fixture
def wall() -> FakeWall:
    return FakeWall(WALL_START)


def running(wall: FakeWall, speed: float = 360.0) -> SimClock:
    return SimClock.start(SIM_START, wall, speed_factor=speed, paused=False)


def test_paused_clock_does_not_move(wall: FakeWall) -> None:
    clock = SimClock.start(SIM_START, wall, speed_factor=360.0, paused=True)

    wall.tick(timedelta(hours=3))

    assert clock.now() == SIM_START


def test_running_clock_applies_speed_factor(wall: FakeWall) -> None:
    clock = running(wall, speed=360.0)

    wall.tick(timedelta(seconds=10))

    assert clock.now() == SIM_START + timedelta(hours=1)


def test_pause_then_resume_has_no_jump(wall: FakeWall) -> None:
    clock = running(wall, speed=60.0)
    wall.tick(timedelta(minutes=1))  # +1 h simulated
    clock.pause()
    wall.tick(timedelta(hours=5))  # ignored while paused
    clock.resume()

    assert clock.now() == SIM_START + timedelta(hours=1)
    wall.tick(timedelta(minutes=1))
    assert clock.now() == SIM_START + timedelta(hours=2)


def test_set_speed_while_paused_then_resume_has_no_jump(wall: FakeWall) -> None:
    clock = running(wall, speed=60.0)
    wall.tick(timedelta(minutes=1))  # +1 h simulated
    clock.pause()
    wall.tick(timedelta(minutes=10))
    clock.set_speed(3600.0)
    wall.tick(timedelta(minutes=10))
    clock.resume()

    assert clock.now() == SIM_START + timedelta(hours=1)
    wall.tick(timedelta(seconds=1))
    assert clock.now() == SIM_START + timedelta(hours=2)


def test_set_speed_while_running_keeps_elapsed_time_at_old_speed(wall: FakeWall) -> None:
    clock = running(wall, speed=60.0)
    wall.tick(timedelta(minutes=1))  # +1 h at x60
    clock.set_speed(3600.0)

    assert clock.now() == SIM_START + timedelta(hours=1)
    wall.tick(timedelta(seconds=1))  # +1 h at x3600
    assert clock.now() == SIM_START + timedelta(hours=2)


def test_advance_jumps_forward_paused_or_running(wall: FakeWall) -> None:
    clock = SimClock.start(SIM_START, wall, paused=True)

    assert clock.advance(timedelta(hours=7)) is True
    assert clock.now() == SIM_START + timedelta(hours=7)


def test_advance_by_zero_changes_nothing(wall: FakeWall) -> None:
    clock = running(wall)
    before = clock.state

    assert clock.advance(timedelta(0)) is False
    assert clock.state == before


def test_advance_backwards_is_rejected(wall: FakeWall) -> None:
    clock = running(wall)

    with pytest.raises(ValueError, match="backwards"):
        clock.advance(timedelta(seconds=-1))


@pytest.mark.parametrize("factor", [0.0, -1.0, math.inf, math.nan])
def test_invalid_speed_is_rejected(wall: FakeWall, factor: float) -> None:
    clock = running(wall)

    with pytest.raises(ValueError, match="speed factor"):
        clock.set_speed(factor)


def test_no_op_operations_report_no_change(wall: FakeWall) -> None:
    clock = running(wall, speed=60.0)

    assert clock.resume() is False
    assert clock.set_speed(60.0) is False
    assert clock.pause() is True
    assert clock.pause() is False


def test_now_never_moves_backwards_when_wall_clock_does(wall: FakeWall) -> None:
    clock = running(wall, speed=60.0)
    wall.tick(timedelta(minutes=2))
    reached = clock.now()

    wall.tick(timedelta(minutes=-1))

    assert clock.now() == reached


def test_state_round_trip_resumes_at_the_same_time(wall: FakeWall) -> None:
    clock = running(wall, speed=60.0)
    wall.tick(timedelta(minutes=3))

    restored = SimClock(clock.state, wall)

    assert restored.now() == clock.now()
    wall.tick(timedelta(minutes=1))
    assert restored.now() == clock.now()


def test_naive_start_is_rejected(wall: FakeWall) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        SimClock.start(datetime(2026, 10, 27, 6, 0), wall)
