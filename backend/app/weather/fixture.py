"""Rain forecast from recorded Open-Meteo hourly responses (D047).

Never reaches the network. An Open-Meteo hourly `precipitation` value at
time T is the total of the hour ending at T. The window (at, at + 24 h] is
covered by every hour that overlaps it; an hour cut by the window counts
whole, which can only overstate rain and so only makes the gate stricter.
If any of those hours is missing or null, the forecast is unknown (None)
and the gate holds the irrigation (D027).
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
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
    cyclic: bool = False  # the demo's (D095): past the last hour, the series starts over

    def mm(self, hour_end: datetime) -> float | None:
        """The rain of the hour ending at `hour_end`; None when the series does not cover it."""
        if hour_end in self.mm_by_hour_end or not self.cyclic or not self.mm_by_hour_end:
            return self.mm_by_hour_end.get(hour_end)
        first, last = min(self.mm_by_hour_end), max(self.mm_by_hour_end)
        period = last - first + HOUR
        return self.mm_by_hour_end.get(first + (hour_end - first) % period)

    def covers(self, hour_end: datetime) -> bool:
        return bool(self.mm_by_hour_end) and min(self.mm_by_hour_end) <= hour_end <= max(
            self.mm_by_hour_end
        )

    def next_24h_mm(self, at: datetime) -> float | None:
        """Sum of the hours ending in (at, ceil(at + 24 h)]: 24 of them, or 25 off the hour."""
        values: list[float | None] = []
        end = _hour_floor(at) + HOUR
        while end - HOUR < at + WINDOW:
            values.append(self.mm(end))
            end += HOUR
        known = [value for value in values if value is not None]
        return round(sum(known), 3) if len(known) == len(values) else None


@dataclass(frozen=True)
class HourlyOutlook:
    """What the UI shows: the hours ahead and the 24 h total the gate uses (D095)."""

    latitude: float
    longitude: float
    hours: tuple[tuple[datetime, float | None], ...]  # (end of the hour, mm)
    next_24h_mm: float | None
    repeated: bool  # some hours come from the start of the series again (demo only)


class FixtureForecast:
    """Implements `ForecastProvider` from every `*.json` in a directory."""

    def __init__(self, locations: Sequence[HourlyRain], nearest_anywhere: bool = False) -> None:
        # The demo's stand-ins (D089, D095): the nearest location however far, and a
        # series that starts over after its last hour, so a long demo keeps a forecast.
        self._locations = tuple(replace(loc, cyclic=nearest_anywhere) for loc in locations)
        self._anywhere = nearest_anywhere

    @classmethod
    def from_directory(cls, directory: Path, nearest_anywhere: bool = False) -> "FixtureForecast":
        files = sorted(directory.glob("*.json"))
        if not files:
            raise ConfigError(f"no Open-Meteo fixtures in {directory}")
        return cls([load_open_meteo(path) for path in files], nearest_anywhere)

    def rain_next_24h_mm(self, lat: float, lon: float, at: datetime) -> float | None:
        if at.tzinfo is None:
            raise ValueError("forecast time must be timezone-aware")
        location = self._nearest(lat, lon)
        return None if location is None else location.next_24h_mm(at.astimezone(UTC))

    def hourly(self, lat: float, lon: float, at: datetime, hours: int) -> HourlyOutlook | None:
        """The `hours` hours after `at`, as the gate reads them; None: no location covers it."""
        location = self._nearest(lat, lon)
        if location is None:
            return None
        start = _hour_floor(at.astimezone(UTC)) + HOUR
        ends = [start + n * HOUR for n in range(hours)]
        repeated = any(not location.covers(end) and location.mm(end) is not None for end in ends)
        return HourlyOutlook(
            location.latitude,
            location.longitude,
            tuple((end, location.mm(end)) for end in ends),
            location.next_24h_mm(at.astimezone(UTC)),
            repeated,
        )

    def _nearest(self, lat: float, lon: float) -> HourlyRain | None:
        close = [
            location
            for location in self._locations
            if self._anywhere
            or (
                abs(location.latitude - lat) <= MAX_COORDINATE_DELTA_DEG
                and abs(location.longitude - lon) <= MAX_COORDINATE_DELTA_DEG
            )
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
