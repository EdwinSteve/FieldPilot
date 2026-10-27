"""Baseline weather for the simulator, evaluated over integration intervals."""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

_SECONDS_PER_DAY = 86_400
_HOUR_OF_MAX_TEMPERATURE = 15.0


@dataclass(frozen=True)
class IntervalWeather:
    """Weather over one integration interval. Amounts are totals for the interval."""

    temperature_c: float
    relative_humidity_pct: float
    rain_mm: float
    et0_mm: float


@dataclass(frozen=True)
class BaseWeather:
    """Dry baseline with a sinusoidal daily cycle. Scenarios modify it."""

    t_min_c: float = 14.0
    t_max_c: float = 28.0
    rh_min_pct: float = 45.0
    rh_max_pct: float = 90.0
    et0_mm_per_day: float = 4.5
    utc_offset_hours: float = -5.0

    def over(self, start: datetime, end: datetime) -> IntervalWeather:
        """Weather for [start, end): conditions at the midpoint, amounts pro rata."""
        midpoint = start + (end - start) / 2
        phase = self._daily_phase(midpoint)  # 1 at the hottest hour, -1 twelve hours later
        temperature = _between(self.t_min_c, self.t_max_c, phase)
        humidity = _between(self.rh_min_pct, self.rh_max_pct, -phase)
        days = (end - start) / timedelta(days=1)
        return IntervalWeather(
            temperature_c=temperature,
            relative_humidity_pct=humidity,
            rain_mm=0.0,
            et0_mm=self.et0_mm_per_day * days,
        )

    def _daily_phase(self, moment: datetime) -> float:
        local = moment + timedelta(hours=self.utc_offset_hours)
        seconds = local.hour * 3600 + local.minute * 60 + local.second
        hours_from_peak = seconds / 3600 - _HOUR_OF_MAX_TEMPERATURE
        return math.cos(2 * math.pi * hours_from_peak * 3600 / _SECONDS_PER_DAY)


def _between(low: float, high: float, phase: float) -> float:
    return low + (high - low) * (phase + 1) / 2
