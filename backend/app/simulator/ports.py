"""Field I/O interfaces. A real hardware adapter would implement the same ones.

They are deliberately separate: the actuator (step 6) depends only on
`ValveController`, and monitoring depends only on `SensorSource`.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class ZoneSnapshot:
    """What a zone's sensors report at one moment."""

    zone_id: int
    at: datetime
    soil_moisture_vwc: float  # volumetric water content, %
    soil_moisture_pct_of_fc: float  # percent of field capacity (D015)
    temperature_c: float
    relative_humidity_pct: float
    rain_mm_last_interval: float


@dataclass(frozen=True)
class ValveStatus:
    zone_id: int
    is_open: bool
    target_mm: float
    applied_mm: float


class SensorSource(Protocol):
    def read(self, zone_id: int, at: datetime) -> ZoneSnapshot: ...


class ValveController(Protocol):
    def open(self, zone_id: int, target_mm: float, rate_mm_per_h: float, at: datetime) -> None: ...
    def close(self, zone_id: int, at: datetime) -> float: ...
    def status(self, zone_id: int, at: datetime) -> ValveStatus: ...
