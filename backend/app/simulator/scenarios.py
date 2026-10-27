"""Weather scenarios injected into the simulator.

New scenarios are new classes implementing `Scenario`; the simulator does
not change (open/closed). Effects are proportional to the overlap between
the scenario window and each integration interval, so results do not depend
on how the window aligns with the integration grid.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from app.domain.models import JsonObject
from app.simulator.weather import IntervalWeather


class Scenario(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def start(self) -> datetime: ...
    @property
    def end(self) -> datetime: ...

    def apply(self, weather: IntervalWeather, start: datetime, end: datetime) -> IntervalWeather:
        """Modify the weather of the interval [start, end)."""
        ...

    def describe(self) -> JsonObject:
        """Parameters for the event log."""
        ...


def is_active(scenario: Scenario, at: datetime) -> bool:
    """True while `at` is inside the scenario window [start, end)."""
    return scenario.start <= at < scenario.end


def overlap_fraction(scenario: Scenario, start: datetime, end: datetime) -> float:
    """Share of the interval [start, end) covered by the scenario window."""
    covered = min(end, scenario.end) - max(start, scenario.start)
    return max(covered, timedelta(0)) / (end - start)


def _ensure_window(start: datetime, end: datetime) -> None:
    if end <= start:
        raise ValueError("scenario must end after it starts")


@dataclass(frozen=True)
class DroughtScenario:
    """Hot, dry spell: no rain, higher ET0 and temperature."""

    start: datetime
    end: datetime
    et0_multiplier: float = 2.0
    temperature_offset_c: float = 5.0
    name: str = "drought"

    def __post_init__(self) -> None:
        _ensure_window(self.start, self.end)
        if self.et0_multiplier < 1:
            raise ValueError("a drought cannot lower evapotranspiration")

    def apply(self, weather: IntervalWeather, start: datetime, end: datetime) -> IntervalWeather:
        share = overlap_fraction(self, start, end)
        if share == 0:
            return weather
        return IntervalWeather(
            temperature_c=weather.temperature_c + self.temperature_offset_c * share,
            relative_humidity_pct=weather.relative_humidity_pct * (1 - 0.3 * share),
            rain_mm=weather.rain_mm * (1 - share),
            et0_mm=weather.et0_mm * (1 + (self.et0_multiplier - 1) * share),
        )

    def describe(self) -> JsonObject:
        return {
            "name": self.name,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "et0_multiplier": self.et0_multiplier,
            "temperature_offset_c": self.temperature_offset_c,
        }


@dataclass(frozen=True)
class HeavyRainScenario:
    """`total_mm` of rain spread evenly over the window."""

    start: datetime
    end: datetime
    total_mm: float = 40.0
    name: str = "heavy_rain"

    def __post_init__(self) -> None:
        _ensure_window(self.start, self.end)
        if self.total_mm <= 0:
            raise ValueError("heavy rain needs a positive amount")

    def apply(self, weather: IntervalWeather, start: datetime, end: datetime) -> IntervalWeather:
        share = overlap_fraction(self, start, end)
        if share == 0:
            return weather
        rain = self.total_mm * (share * (end - start) / (self.end - self.start))
        return IntervalWeather(
            temperature_c=weather.temperature_c - 3.0 * share,
            relative_humidity_pct=weather.relative_humidity_pct
            + (95.0 - weather.relative_humidity_pct) * share,
            rain_mm=weather.rain_mm + rain,
            et0_mm=weather.et0_mm * (1 - 0.7 * share),
        )

    def describe(self) -> JsonObject:
        return {
            "name": self.name,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "total_mm": self.total_mm,
        }
