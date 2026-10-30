"""Plots, zones, readings and crop cycles: read-only."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ContainerDep
from app.api.schemas import CycleOut, PlotOut, SensorReadingsOut, ZoneOut

router = APIRouter(tags=["farm"])


@router.get("/plots")
def list_plots(container: ContainerDep) -> list[PlotOut]:
    return [PlotOut.of(p) for p in container.queries.plots()]


@router.get("/plots/{plot_id}/zones")
def list_zones(plot_id: int, container: ContainerDep) -> list[ZoneOut]:
    return [ZoneOut.of(z) for z in container.queries.zones(plot_id)]


@router.get("/readings")
def list_readings(
    zone_id: int,
    container: ContainerDep,
    limit: Annotated[int, Query(ge=1, le=5000)] = 500,
) -> list[SensorReadingsOut]:
    return [SensorReadingsOut.of(s) for s in container.queries.readings(zone_id, limit)]


@router.get("/cycles")
def list_cycles(container: ContainerDep) -> list[CycleOut]:
    return [CycleOut.of(c) for c in container.queries.cycles()]


@router.get("/cycles/{cycle_id}")
def get_cycle(cycle_id: int, container: ContainerDep) -> CycleOut:
    return CycleOut.of(container.queries.cycle(cycle_id))
