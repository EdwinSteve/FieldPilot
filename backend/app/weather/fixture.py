"""Rain forecast from recorded Open-Meteo hourly responses (D047).

Never reaches the network. An Open-Meteo hourly `precipitation` value at
time T is the total of the hour ending at T. The window (at, at + 24 h] is
covered by every hour that overlaps it; an hour cut by the window counts
whole, which can only overstate rain and so only makes the gate stricter.
If any of those hours is missing or null, the forecast is unknown (None)
and the gate holds the irrigation (D027).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.domain.errors import ConfigError

WINDOW = timedelta(hours=24)
HOUR = timedelta(hours=1)
# Open-Meteo snaps coordinates to its grid; a plot this close uses the fixture.
MAX_COORDINATE_DELTA_DEG = 0.1


class _Hourly(BaseModel):
    time: list[str]
    precipitation: list[float | None]


class _OpenMeteoResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    latitude: float
    longitude: float
    utc_offset_seconds: int
    hourly: _Hourly


@dataclass(frozen=True)
class HourlyRain:
    """One location's hourly rain, keyed by the aware UTC end of each hour."""

    latitude: float
    longitude: float
    mm_by_hour_end: dict[datetime, float | None]

    def next_24h_mm(self, at: datetime) -> float | None:
        """Sum of the hours ending in (at, ceil(at + 24 h)]: 24 of them, or 25 off the hour."""
        values: list[float | None] = []
        end = _hour_floor(at) + HOUR
        while end - HOUR < at + WINDOW:
            values.append(self.mm_by_hour_end.get(end))
            end += HOUR
        known = [value for value in values if value is not None]
        return round(sum(known), 3) if len(known) == len(values) else None


class FixtureForecast:
    """Implements `ForecastProvider` from every `*.json` in a directory."""

    def __init__(self, locations: Sequence[HourlyRain]) -> None:
        self._locations = tuple(locations)

    @classmethod
    def from_directory(cls, directory: Path) -> "FixtureForecast":
        files = sorted(directory.glob("*.json"))
        if not files:
            raise ConfigError(f"no Open-Meteo fixtures in {directory}")
        return cls([load_open_meteo(path) for path in files])

    def rain_next_24h_mm(self, lat: float, lon: float, at: datetime) -> float | None:
        if at.tzinfo is None:
            raise ValueError("forecast time must be timezone-aware")
        location = self._nearest(lat, lon)
        return None if location is None else location.next_24h_mm(at.astimezone(UTC))

    def _nearest(self, lat: float, lon: float) -> HourlyRain | None:
        close = [
            location
            for location in self._locations
            if abs(location.latitude - lat) <= MAX_COORDINATE_DELTA_DEG
            and abs(location.longitude - lon) <= MAX_COORDINATE_DELTA_DEG
        ]
        return min(
            close,
            key=lambda location: abs(location.latitude - lat) + abs(location.longitude - lon),
            default=None,
        )


def load_open_meteo(path: Path) -> HourlyRain:
    response = _OpenMeteoResponse.model_validate_json(path.read_text(encoding="utf-8"))
    hourly = response.hourly
    if len(hourly.time) != len(hourly.precipitation):
        raise ConfigError(f"{path.name}: hourly time and precipitation differ in length")
    offset = timedelta(seconds=response.utc_offset_seconds)
    return HourlyRain(
        response.latitude,
        response.longitude,
        {
            datetime.fromisoformat(stamp).replace(tzinfo=UTC) - offset: mm
            for stamp, mm in zip(hourly.time, hourly.precipitation, strict=True)
        },
    )


def _hour_floor(at: datetime) -> datetime:
    return at.replace(minute=0, second=0, microsecond=0)
