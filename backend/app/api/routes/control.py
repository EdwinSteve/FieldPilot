"""The simulated clock, the simulation tick and the emergency stop (D011, D022, D064, D065)."""

from datetime import timedelta

from fastapi import APIRouter, HTTPException

from app.api.deps import FARMER, ContainerDep
from app.api.schemas import (
    ClockIn,
    ClockOut,
    EmergencyStopIn,
    EmergencyStopOut,
    TaskOut,
    TickOut,
)

router = APIRouter(tags=["control"])


@router.get("/clock")
def get_clock(container: ContainerDep) -> ClockOut:
    return _clock(container)


@router.post("/clock")
def change_clock(body: ClockIn, container: ContainerDep) -> ClockOut:
    service = container.clock_service
    match body.action:
        case "pause":
            service.pause(FARMER)
        case "resume":
            service.resume(FARMER)
        case "speed":
            if body.speed_factor is None:
                raise HTTPException(status_code=422, detail="speed needs speed_factor")
            service.set_speed(FARMER, body.speed_factor)
        case "advance":
            if body.advance_seconds is None:
                raise HTTPException(status_code=422, detail="advance needs advance_seconds")
            service.advance(FARMER, timedelta(seconds=body.advance_seconds))
    return _clock(container)


@router.post("/simulation/tick")
def tick(container: ContainerDep) -> TickOut:
    result = container.ticker.tick()
    tasks = [TaskOut.of(container.queries.task_view(t)) for t in result.tasks]
    return TickOut.of(result, tasks)


@router.get("/emergency-stop")
def get_emergency_stop(container: ContainerDep) -> EmergencyStopOut:
    return EmergencyStopOut.of(container.emergency.state())


@router.post("/emergency-stop")
def set_emergency_stop(body: EmergencyStopIn, container: ContainerDep) -> EmergencyStopOut:
    return EmergencyStopOut.of(container.emergency.set(body.active, FARMER))


def _clock(container: ContainerDep) -> ClockOut:
    clock = container.runtime.clock
    state = clock.state
    return ClockOut(now=clock.now(), speed_factor=state.speed_factor, paused=state.paused)
