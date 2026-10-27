"""Field simulator: implements `SensorSource` and `ValveController`.

Time only moves forward. `advance_to(t)` integrates whole fixed substeps on a
grid anchored at the start time, so the state is identical whether it is
reached in one call or many. Sensor noise is derived from (seed, zone, time),
so reading twice gives the same value and the call pattern does not matter.
"""

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.domain.errors import NotFoundError, ValveError
from app.domain.units import pct_of_field_capacity
from app.simulator.irrigation import IrrigationRun
from app.simulator.ports import ValveStatus, ZoneSnapshot
from app.simulator.scenarios import Scenario, is_active
from app.simulator.water_balance import SoilParams, WaterInputs, step_water_balance
from app.simulator.weather import BaseWeather, IntervalWeather

DEFAULT_SUBSTEP = timedelta(minutes=15)


@dataclass(frozen=True)
class SensorNoise:
    """Standard deviations of the noise added to reported values."""

    moisture_vwc: float = 0.3
    temperature_c: float = 0.2
    humidity_pct: float = 1.0


@dataclass
class _ZoneState:
    soil: SoilParams
    vwc: float
    crop_coefficient: float
    runs: list[IrrigationRun] = field(default_factory=list)
    last_rain_mm: float = 0.0


class FieldSimulator:
    """In-memory field model. Its state is not persisted (D014)."""

    def __init__(
        self,
        start: datetime,
        weather: BaseWeather | None = None,
        seed: int = 0,
        substep: timedelta = DEFAULT_SUBSTEP,
        noise: SensorNoise | None = None,
    ) -> None:
        if substep <= timedelta(0):
            raise ValueError("substep must be positive")
        self._weather = weather or BaseWeather()
        self._seed = seed
        self._substep = substep
        self._noise = noise or SensorNoise()
        self._time = start
        self._latest_seen = start
        self._zones: dict[int, _ZoneState] = {}
        self._scenarios: list[Scenario] = []

    @property
    def integrated_until(self) -> datetime:
        """Last grid point the state has been integrated to."""
        return self._time

    # --- setup -----------------------------------------------------------

    def add_zone(
        self, zone_id: int, soil: SoilParams, initial_vwc: float, crop_coefficient: float = 1.0
    ) -> None:
        if zone_id in self._zones:
            raise ValueError(f"zone {zone_id} already simulated")
        self._zones[zone_id] = _ZoneState(soil, initial_vwc, crop_coefficient)

    def set_crop_coefficient(self, zone_id: int, crop_coefficient: float) -> None:
        self._zone(zone_id).crop_coefficient = crop_coefficient

    # --- scenarios -------------------------------------------------------

    def inject(self, scenario: Scenario) -> None:
        """Activate a scenario. It cannot start in the already-simulated past."""
        if scenario.start < self._latest_seen:
            raise ValueError("scenario cannot start before the current simulated time")
        self._scenarios.append(scenario)

    def active_scenarios(self, at: datetime) -> tuple[Scenario, ...]:
        """Scenarios in effect at `at`. The UI reads this, not a stored copy (D014)."""
        return tuple(s for s in self._scenarios if is_active(s, at))

    # --- time ------------------------------------------------------------

    def advance_to(self, at: datetime) -> None:
        """Integrate every whole substep up to `at`."""
        self._observe(at)
        while self._time + self._substep <= at:
            self._integrate(self._time, self._time + self._substep)
            self._time += self._substep

    # --- SensorSource ----------------------------------------------------

    def read(self, zone_id: int, at: datetime) -> ZoneSnapshot:
        """Sensor values at the last grid point not after `at`."""
        zone = self._zone(zone_id)
        self.advance_to(at)
        weather = self._interval_weather(self._time - self._substep, self._time)
        rng = random.Random(f"{self._seed}:{zone_id}:{self._time.isoformat()}")
        vwc = zone.vwc + rng.gauss(0, self._noise.moisture_vwc)
        return ZoneSnapshot(
            zone_id=zone_id,
            at=self._time,
            soil_moisture_vwc=vwc,
            soil_moisture_pct_of_fc=pct_of_field_capacity(vwc, zone.soil.field_capacity_vwc),
            temperature_c=weather.temperature_c + rng.gauss(0, self._noise.temperature_c),
            relative_humidity_pct=weather.relative_humidity_pct
            + rng.gauss(0, self._noise.humidity_pct),
            rain_mm_last_interval=zone.last_rain_mm,
        )

    # --- ValveController -------------------------------------------------

    def open(self, zone_id: int, target_mm: float, rate_mm_per_h: float, at: datetime) -> None:
        zone = self._zone(zone_id)
        self._observe(at)
        if zone.runs and zone.runs[-1].is_open(at):
            raise ValveError(f"valve of zone {zone_id} is already open")
        zone.runs.append(IrrigationRun(at, target_mm, rate_mm_per_h))

    def close(self, zone_id: int, at: datetime) -> float:
        """Close an open valve and return the millimetres actually applied."""
        zone = self._zone(zone_id)
        self._observe(at)
        if not zone.runs or not zone.runs[-1].is_open(at):
            raise ValveError(f"valve of zone {zone_id} is not open")
        zone.runs[-1] = zone.runs[-1].closed(at)
        return zone.runs[-1].applied_until(at)

    def status(self, zone_id: int, at: datetime) -> ValveStatus:
        zone = self._zone(zone_id)
        self._observe(at)
        if not zone.runs:
            return ValveStatus(zone_id, is_open=False, target_mm=0.0, applied_mm=0.0)
        run = zone.runs[-1]
        return ValveStatus(
            zone_id,
            is_open=run.is_open(at),
            target_mm=run.target_mm,
            applied_mm=run.applied_until(at),
        )

    # --- internals -------------------------------------------------------

    def _observe(self, at: datetime) -> None:
        if at < self._latest_seen:
            raise ValueError("simulated time cannot go backwards")
        self._latest_seen = at

    def _zone(self, zone_id: int) -> _ZoneState:
        try:
            return self._zones[zone_id]
        except KeyError:
            raise NotFoundError("Zone", zone_id) from None

    def _interval_weather(self, start: datetime, end: datetime) -> IntervalWeather:
        weather = self._weather.over(start, end)
        for scenario in self._scenarios:
            weather = scenario.apply(weather, start, end)
        return weather

    def _integrate(self, start: datetime, end: datetime) -> None:
        weather = self._interval_weather(start, end)
        interval_days = (end - start) / timedelta(days=1)
        for zone in self._zones.values():
            irrigation = sum(run.applied_between(start, end) for run in zone.runs)
            inputs = WaterInputs(
                rain_mm=weather.rain_mm,
                irrigation_mm=irrigation,
                et0_mm=weather.et0_mm,
                crop_coefficient=zone.crop_coefficient,
                interval_days=interval_days,
            )
            zone.vwc = step_water_balance(zone.vwc, inputs, zone.soil).vwc
            zone.last_rain_mm = weather.rain_mm
