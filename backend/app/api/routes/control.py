"""The simulated clock, the simulation tick and the emergency stop (D011, D022, D064, D065)."""

from datetime import timedelta

from fastapi import APIRouter, HTTPException
from pydantic import JsonValue

from app.api.auth import FarmerDep
from app.api.deps import ContainerDep
from app.api.schemas import (
    ClockIn,
    ClockOut,
    EmergencyStopIn,
    EmergencyStopOut,
    ScenarioIn,
    ScenarioStatusOut,
    TaskOut,
    TickOut,
)

router = APIRouter(tags=["control"])


@router.get("/clock")
def get_clock(container: ContainerDep) -> ClockOut:
    return _clock(container)


@router.post("/clock")
def change_clock(body: ClockIn, farmer: FarmerDep, container: ContainerDep) -> ClockOut:
    service = container.clock_service
    match body.action:
        case "pause":
            service.pause(farmer.actor)
        case "resume":
            service.resume(farmer.actor)
        case "speed":
            if body.speed_factor is None:
                raise HTTPException(status_code=422, detail="speed needs speed_factor")
            service.set_speed(farmer.actor, body.speed_factor)
        case "advance":
            if body.advance_seconds is None:
                raise HTTPException(status_code=422, detail="advance needs advance_seconds")
            service.advance(farmer.actor, timedelta(seconds=body.advance_seconds))
    return _clock(container)


@router.post("/simulation/tick")
def tick(container: ContainerDep) -> TickOut:
    result = container.ticker.tick()
    tasks = [TaskOut.of(container.queries.task_view(t)) for t in result.tasks]
    return TickOut.of(result, tasks)


@router.get("/simulation/status")
def simulation_status(container: ContainerDep) -> ScenarioStatusOut:
    return ScenarioStatusOut.of(container.scenarios.status())


@router.post("/simulation/scenarios")
def inject_scenario(
    body: ScenarioIn, farmer: FarmerDep, container: ContainerDep
) -> dict[str, JsonValue]:
    return dict(container.scenarios.inject(body.scenario(), farmer.actor))


@router.get("/emergency-stop")
def get_emergency_stop(container: ContainerDep) -> EmergencyStopOut:
    return EmergencyStopOut.of(container.emergency.state())


@router.post("/emergency-stop")
def set_emergency_stop(
    body: EmergencyStopIn, farmer: FarmerDep, container: ContainerDep
) -> EmergencyStopOut:
    return EmergencyStopOut.of(container.emergency.set(body.active, farmer.actor))


def _clock(container: ContainerDep) -> ClockOut:
    clock = container.runtime.clock
    state = clock.state
    return ClockOut(now=clock.now(), speed_factor=state.speed_factor, paused=state.paused)
