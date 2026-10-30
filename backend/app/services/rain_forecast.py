"""The gate's `RainForecast` port, answered by a coordinates-based provider (D047)."""

from collections.abc import Callable
from datetime import datetime

from app.persistence.ports import UnitOfWork
from app.weather.ports import ForecastProvider

UowFactory = Callable[[], UnitOfWork]


class PlotRainForecast:
    """Looks up the plot's coordinates; the provider never sees plot ids."""

    def __init__(self, uow: UowFactory, provider: ForecastProvider) -> None:
        self._uow = uow
        self._provider = provider

    def rain_mm_next_24h(self, plot_id: int, at: datetime) -> float | None:
        with self._uow() as u:
            plot = u.plots.get(plot_id)
        return self._provider.rain_next_24h_mm(plot.latitude, plot.longitude, at)
