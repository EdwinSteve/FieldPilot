"""Plots, their site data, the sowing and the harvest the farmer confirms (D083, docs/api.md)."""

from fastapi import APIRouter

from app.api.auth import FarmerDep
from app.api.deps import ContainerDep
from app.api.schemas import (
    CycleOut,
    HarvestIn,
    LotOut,
    NewCycleIn,
    NewPlotIn,
    PlotOut,
    SiteOut,
    WeatherOut,
)
from app.services.cycles import Harvest, NewCycle
from app.services.plots import NewPlot

router = APIRouter(tags=["lifecycle"])


@router.get("/plots")
def list_plots(farmer: FarmerDep, container: ContainerDep) -> list[PlotOut]:
    """The caller's plots; an admin sees all."""
    return [PlotOut.of(p) for p in container.plots.visible(farmer)]


@router.post("/plots", status_code=201)
def create_plot(body: NewPlotIn, farmer: FarmerDep, container: ContainerDep) -> PlotOut:
    """The farmer becomes a member; the site data starts building (GET /plots/{id}/site)."""
    form = NewPlot(
        body.name, body.municipality, body.department, body.latitude, body.longitude,
        body.area_ha,
    )  # fmt: skip
    return PlotOut.of(container.plots.create(farmer, form))


@router.get("/plots/{plot_id}/site")
def plot_site(plot_id: int, container: ContainerDep) -> SiteOut:
    return SiteOut.of(container.plots.site(plot_id))


@router.get("/plots/{plot_id}/weather")
def plot_weather(plot_id: int, container: ContainerDep) -> WeatherOut:
    """The rain ahead, exactly as the autonomy gate reads it, with its source (D095)."""
    return WeatherOut.of(container.weather.outlook(plot_id))


@router.post("/plots/{plot_id}/site", status_code=202)
def rebuild_plot_site(plot_id: int, container: ContainerDep) -> SiteOut:
    return SiteOut.of(container.plots.refresh_site(plot_id))


@router.post("/plots/{plot_id}/cycles", status_code=201)
def start_cycle(
    plot_id: int, body: NewCycleIn, farmer: FarmerDep, container: ContainerDep
) -> CycleOut:
    """The sowing confirmation; a crop outside the top 3 needs accept_own_risk."""
    cycle = container.cycles.start(
        farmer, plot_id, NewCycle(body.crop, body.sowing_date, body.accept_own_risk)
    )
    return CycleOut.of(container.queries.cycle(_stored(cycle.id)))


@router.post("/cycles/{cycle_id}/harvest", status_code=201)
def harvest(cycle_id: int, body: HarvestIn, farmer: FarmerDep, container: ContainerDep) -> LotOut:
    """The harvest confirmation: the only way a lot is born (§4.14)."""
    cycle = container.queries.cycle(cycle_id).cycle
    container.access.require_farm(farmer, cycle.plot_id)  # the plot is not in the path
    lot = container.cycles.harvest(
        farmer, cycle_id, Harvest(body.harvested_on, body.quantity_kg, body.grade)
    )
    return LotOut.of(lot)


@router.get("/plots/{plot_id}/lots")
def list_lots(plot_id: int, container: ContainerDep) -> list[LotOut]:
    return [LotOut.of(lot) for lot in container.queries.lots(plot_id)]


def _stored(entity_id: int | None) -> int:
    if entity_id is None:
        raise ValueError("entity was not stored")
    return entity_id
