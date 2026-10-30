"""The forecast port the services depend on (§4.9, D047)."""

from datetime import datetime
from typing import Protocol


class ForecastProvider(Protocol):
    def rain_next_24h_mm(self, lat: float, lon: float, at: datetime) -> float | None:
        """Rain expected in the 24 h after `at`, or None when the data cannot say."""
        ...
