"""Exact bookkeeping of irrigation runs, independent of the integration grid."""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

_HOUR = timedelta(hours=1)


@dataclass(frozen=True)
class IrrigationRun:
    """One valve opening: water flows at a constant rate until target or close."""

    started_at: datetime
    target_mm: float
    rate_mm_per_h: float
    closed_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.target_mm <= 0 or self.rate_mm_per_h <= 0:
            raise ValueError("target and rate must be positive")

    @property
    def natural_end(self) -> datetime:
        """When the target is reached if nobody closes the valve."""
        return self.started_at + _HOUR * (self.target_mm / self.rate_mm_per_h)

    @property
    def end(self) -> datetime:
        if self.closed_at is None:
            return self.natural_end
        return min(self.closed_at, self.natural_end)

    def is_open(self, at: datetime) -> bool:
        return self.closed_at is None and at < self.natural_end

    def applied_until(self, at: datetime) -> float:
        """Water applied from the start until `at`: rate x elapsed, capped at target."""
        flowing = max(min(at, self.end) - self.started_at, timedelta(0))
        return min(self.rate_mm_per_h * (flowing / _HOUR), self.target_mm)

    def applied_between(self, start: datetime, end: datetime) -> float:
        return self.applied_until(end) - self.applied_until(start)

    def closed(self, at: datetime) -> "IrrigationRun":
        return replace(self, closed_at=at)
