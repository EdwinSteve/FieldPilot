"""Plots, zones, readings, crop cycles and the planting plan: read-only."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.api.auth import FarmerDep
from app.api.deps import ContainerDep
from app.api.schemas import (
    CropOut,
    CycleOut,
    ImageryOut,
    PlantingPlanOut,
    SensorReadingsOut,
    ZoneOut,
)
from app.services.planning import MAX_WEEKS, PlanRequest

router = APIRouter(tags=["farm"])


@router.get("/plots/{plot_id}/zones")
def list_zones(plot_id: int, container: ContainerDep) -> list[ZoneOut]:
    return [ZoneOut.of(z) for z in container.queries.zones(plot_id)]


@router.get("/plots/{plot_id}/imagery")
def plot_imagery(plot_id: int, container: ContainerDep) -> ImageryOut:
    return ImageryOut.of(container.queries.imagery(plot_id))


@router.get("/plots/{plot_id}/imagery/image")
def plot_imagery_image(plot_id: int, container: ContainerDep) -> Response:
    """The scene's PNG for the dashboard overlay; 404 when there is no scene (D073)."""
    return Response(container.queries.imagery_image(plot_id), media_type="image/png")


@router.get("/readings")
def list_readings(
    zone_id: int,
    container: ContainerDep,
    limit: Annotated[int, Query(ge=1, le=5000)] = 500,
) -> list[SensorReadingsOut]:
    return [SensorReadingsOut.of(s) for s in container.queries.readings(zone_id, limit)]


@router.get("/plots/{plot_id}/planting-plan")
def planting_plan(
    plot_id: int,
    farmer: FarmerDep,
    container: ContainerDep,
    first_sowing: Annotated[date | None, Query(alias="from")] = None,
    weeks: Annotated[int, Query(ge=1, le=MAX_WEEKS)] = 4,
) -> PlantingPlanOut:
    """What to sow and when (D079): advice only; it never creates a task."""
    request = PlanRequest(plot_id, first_sowing, weeks, farmer.actor)
    return PlantingPlanOut.of(container.planning.plan(request))


@router.get("/crops/{crop}")
def get_crop(crop: str, container: ContainerDep) -> CropOut:
    return CropOut.of(container.queries.crop(crop))


@router.get("/cycles")
def list_cycles(container: ContainerDep) -> list[CycleOut]:
    return [CycleOut.of(c) for c in container.queries.cycles()]


@router.get("/cycles/{cycle_id}")
def get_cycle(cycle_id: int, container: ContainerDep) -> CycleOut:
    return CycleOut.of(container.queries.cycle(cycle_id))
