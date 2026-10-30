from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from app.domain.errors import NotFoundError
from app.persistence.unit_of_work import SqlUnitOfWork
from app.services.rain_forecast import PlotRainForecast
from app.weather.fixture import FixtureForecast
from tests.conftest import OPEN_METEO_DIR, FieldIds

UowFactory = Callable[[], SqlUnitOfWork]
MORNING = datetime(2026, 10, 28, 11, 0, tzinfo=UTC)


class RecordingProvider:
    def __init__(self) -> None:
        self.asked: list[tuple[float, float, datetime]] = []

    def rain_next_24h_mm(self, lat: float, lon: float, at: datetime) -> float | None:
        self.asked.append((lat, lon, at))
        return 3.5


def test_the_provider_is_asked_with_the_plot_coordinates(uow: UowFactory, field: FieldIds) -> None:
    provider = RecordingProvider()

    rain = PlotRainForecast(uow, provider).rain_mm_next_24h(field.plot_id, MORNING)

    assert rain == 3.5
    assert provider.asked == [(2.93, -75.28, MORNING)]


def test_the_demo_farm_gets_a_known_dry_forecast(uow: UowFactory, field: FieldIds) -> None:
    forecast = PlotRainForecast(uow, FixtureForecast.from_directory(OPEN_METEO_DIR))

    assert forecast.rain_mm_next_24h(field.plot_id, MORNING) == 0.0


def test_an_unknown_plot_raises_not_found(uow: UowFactory) -> None:
    with pytest.raises(NotFoundError, match="Plot 99"):
        PlotRainForecast(uow, RecordingProvider()).rain_mm_next_24h(99, MORNING)
