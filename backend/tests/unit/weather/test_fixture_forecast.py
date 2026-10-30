import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.errors import ConfigError
from app.weather.fixture import FixtureForecast, HourlyRain, load_open_meteo
from tests.conftest import OPEN_METEO_DIR

AT = datetime(2026, 10, 28, 11, 0, tzinfo=UTC)
LAT, LON = 2.95, -75.3


def _hours(start: datetime, count: int, mm: float = 0.0) -> dict[datetime, float | None]:
    return {start + timedelta(hours=n): mm for n in range(1, count + 1)}


def _forecast(hours: dict[datetime, float | None]) -> FixtureForecast:
    return FixtureForecast([HourlyRain(LAT, LON, hours)])


def test_on_the_hour_the_window_is_the_next_24_hours() -> None:
    hours = _hours(AT - timedelta(hours=1), 26, mm=1.0)
    hours[AT] = 50.0  # the hour ending at `at` is in the past
    hours[AT + timedelta(hours=25)] = 50.0  # beyond the window

    assert _forecast(hours).rain_next_24h_mm(LAT, LON, AT) == 24.0


def test_off_the_hour_both_cut_hours_count_whole() -> None:
    at = AT + timedelta(minutes=30)
    hours = _hours(AT - timedelta(hours=1), 27, mm=1.0)

    # Hours ending 12:00 ... next day 12:00: 25 of them, overstating on purpose.
    assert _forecast(hours).rain_next_24h_mm(LAT, LON, at) == 25.0


def test_a_missing_hour_makes_the_forecast_unknown() -> None:
    hours = _hours(AT, 24)
    del hours[AT + timedelta(hours=10)]

    assert _forecast(hours).rain_next_24h_mm(LAT, LON, AT) is None


def test_a_null_hour_makes_the_forecast_unknown() -> None:
    hours = _hours(AT, 24)
    hours[AT + timedelta(hours=24)] = None

    assert _forecast(hours).rain_next_24h_mm(LAT, LON, AT) is None


def test_zero_rain_is_a_known_zero() -> None:
    assert _forecast(_hours(AT, 24)).rain_next_24h_mm(LAT, LON, AT) == 0.0


def test_a_window_past_the_fixture_is_unknown() -> None:
    assert _forecast(_hours(AT, 23)).rain_next_24h_mm(LAT, LON, AT) is None


def test_the_nearest_fixture_within_a_tenth_of_a_degree_is_used() -> None:
    near = HourlyRain(2.95, -75.3, _hours(AT, 24, mm=1.0))
    nearer = HourlyRain(2.93, -75.28, _hours(AT, 24, mm=2.0))
    forecast = FixtureForecast([near, nearer])

    assert forecast.rain_next_24h_mm(2.93, -75.28, AT) == 48.0
    assert forecast.rain_next_24h_mm(3.04, -75.3, AT) == 24.0
    assert forecast.rain_next_24h_mm(3.06, -75.3, AT) is None


def test_a_plot_far_from_every_fixture_gets_no_forecast() -> None:
    assert _forecast(_hours(AT, 24)).rain_next_24h_mm(4.6, -74.1, AT) is None


def test_a_naive_time_is_refused() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _forecast(_hours(AT, 24)).rain_next_24h_mm(LAT, LON, AT.replace(tzinfo=None))


def _write(tmp_path: Path, **overrides: object) -> Path:
    body: dict[str, object] = {
        "latitude": LAT,
        "longitude": LON,
        "utc_offset_seconds": -18000,
        "timezone": "America/Bogota",
        "hourly": {"time": ["2026-10-28T06:00", "2026-10-28T07:00"], "precipitation": [0.5, 1.0]},
    }
    body.update(overrides)
    path = tmp_path / "plot.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def test_local_times_are_converted_to_utc(tmp_path: Path) -> None:
    location = load_open_meteo(_write(tmp_path))

    assert location.mm_by_hour_end == {
        datetime(2026, 10, 28, 11, 0, tzinfo=UTC): 0.5,
        datetime(2026, 10, 28, 12, 0, tzinfo=UTC): 1.0,
    }


def test_hourly_arrays_of_different_length_are_refused(tmp_path: Path) -> None:
    path = _write(tmp_path, hourly={"time": ["2026-10-28T06:00"], "precipitation": [0.5, 1.0]})

    with pytest.raises(ConfigError, match="differ in length"):
        load_open_meteo(path)


def test_a_response_without_hourly_data_is_refused(tmp_path: Path) -> None:
    path = _write(tmp_path, hourly=None)

    with pytest.raises(ValidationError):
        load_open_meteo(path)


def test_an_empty_directory_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="no Open-Meteo fixtures"):
        FixtureForecast.from_directory(tmp_path)


# The shipped fixture (data/fixtures/open_meteo/neiva.json).

DEMO_FARM = (2.93, -75.28)


@pytest.fixture(scope="module")
def shipped() -> FixtureForecast:
    return FixtureForecast.from_directory(OPEN_METEO_DIR)


def test_the_demo_morning_is_dry(shipped: FixtureForecast) -> None:
    assert shipped.rain_next_24h_mm(*DEMO_FARM, AT) == 0.0


def test_the_rain_event_exceeds_the_5_mm_limit(shipped: FixtureForecast) -> None:
    morning = datetime(2026, 11, 2, 11, 0, tzinfo=UTC)

    assert shipped.rain_next_24h_mm(*DEMO_FARM, morning) == 12.0


def test_after_the_fixture_ends_the_forecast_is_unknown(shipped: FixtureForecast) -> None:
    assert shipped.rain_next_24h_mm(*DEMO_FARM, datetime(2026, 11, 10, 11, 0, tzinfo=UTC)) is None
