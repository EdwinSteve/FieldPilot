"""The gate's `RainForecast` port (D047), and the same forecast as the UI shows it (D095)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.persistence.ports import UnitOfWork
from app.simulator.clock import Clock
from app.weather.fixture import FixtureForecast
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


@dataclass(frozen=True)
class PlotWeather:
    """The forecast of a plot as the UI shows it: what the gate reads, and where from (D095)."""

    plot_id: int
    source: str  # "open_meteo_fixture", or "open_meteo_fixture_repeated" past its end (demo)
    latitude: float | None  # the forecast's grid point
    longitude: float | None
    as_of: datetime
    rain_next_24h_mm: float | None  # None: unknown, and the gate holds any irrigation
    hours: tuple[tuple[datetime, float | None], ...]


class PlotWeatherService:
    def __init__(self, uow: UowFactory, forecast: FixtureForecast, clock: Clock) -> None:
        self._uow = uow
        self._forecast = forecast
        self._clock = clock

    def outlook(self, plot_id: int, hours: int = 48) -> PlotWeather:
        with self._uow() as u:
            plot = u.plots.get(plot_id)
        now = self._clock.now()
        found = self._forecast.hourly(plot.latitude, plot.longitude, now, hours)
        if found is None:
            return PlotWeather(plot_id, "none", None, None, now, None, ())
        source = "open_meteo_fixture" + ("_repeated" if found.repeated else "")
        return PlotWeather(plot_id, source, found.latitude, found.longitude, now,
                           found.next_24h_mm, found.hours)  # fmt: skip
