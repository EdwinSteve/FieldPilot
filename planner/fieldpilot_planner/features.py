"""Model inputs: the one definition shared by training and serving (README §9).

Training applies these transforms to whole arrays once; the backend applies
them to one plot. Both use the same channel lists, transforms and saved
normalisation, so the two cannot drift.
"""

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import numpy.typing as npt

from fieldpilot_planner.sources.soilgrids import PROPERTIES

F32 = npt.NDArray[np.float32]

HISTORY_DAYS = 365
AHEAD_DAYS = 210
WEATHER_CHANNELS = (
    "t2m", "tmax", "tmin", "rain", "rh", "wind", "radiation", "et0", "gwetroot",
    "radiation_estimated",
)  # fmt: skip
CLIM_CHANNELS = ("t_mean", "t_p10", "t_p90", "rain_mean", "rain_p10", "rain_p90")
SITE_FEATURES = (
    "lat", "lon", "elevation_m", "elevation_minus_cell_m",
    *(f"{p}_0_30" for p in PROPERTIES), *(f"{p}_30_60" for p in PROPERTIES),
)  # fmt: skip
CONTEXT_FEATURES = ("oni", "oni_trend_3m", "doy_sin", "doy_cos")
STATIC_FEATURES = SITE_FEATURES + CONTEXT_FEATURES

# Rain is heavy-tailed: log1p before standardising.
LOG_WEATHER = tuple(i for i, c in enumerate(WEATHER_CHANNELS) if c == "rain")
LOG_CLIM = tuple(i for i, c in enumerate(CLIM_CHANNELS) if c.startswith("rain"))


def _month_shift(year: int, month: int, back: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) - back
    return index // 12, index % 12 + 1


def oni_known_at(oni: Mapping[tuple[int, int], float], sowing: date) -> tuple[float, float]:
    """ONI of the season that ended two months before the sowing month, and its 3-month change.

    CPC publishes a season early in the following month, so a season ending
    two months earlier is always published by the sowing date: no leakage.
    """
    latest = oni[_month_shift(sowing.year, sowing.month, 2)]
    earlier = oni[_month_shift(sowing.year, sowing.month, 5)]
    return latest, latest - earlier


def context_vector(oni: float, oni_trend: float, sowing: date) -> list[float]:
    angle = 2 * math.pi * (sowing.timetuple().tm_yday - 1) / 365.25
    return [oni, oni_trend, math.sin(angle), math.cos(angle)]


def transform_weather(weather: F32) -> F32:
    """[..., channels] in WEATHER_CHANNELS order; returns a transformed copy."""
    out = weather.astype(np.float32, copy=True)
    for i in LOG_WEATHER:
        out[..., i] = np.log1p(np.maximum(out[..., i], 0.0))
    return out


def transform_clim(clim: F32) -> F32:
    out = clim[..., : len(CLIM_CHANNELS)].astype(np.float32, copy=True)
    for i in LOG_CLIM:
        out[..., i] = np.log1p(np.maximum(out[..., i], 0.0))
    return out


def prior_features(b0: F32, cycle_days: F32) -> F32:
    """B0 outcomes [..., C, 5] -> the network's prior: the same scale as its targets.

    rel_yield and success as they are, log1p of irrigation, and heat and cold
    days as fractions of each crop's cycle.
    """
    return np.stack(
        [b0[..., 0], b0[..., 1], np.log1p(np.maximum(b0[..., 2], 0.0)),
         b0[..., 3] / cycle_days, b0[..., 4] / cycle_days],
        axis=-1,
    ).astype(np.float32)  # fmt: skip


@dataclass(frozen=True)
class Standardizer:
    mean: F32
    std: F32

    @classmethod
    def fit(cls, values: F32, axis: tuple[int, ...]) -> "Standardizer":
        mean = np.nanmean(values, axis=axis).astype(np.float32)
        std = np.nanstd(values, axis=axis).astype(np.float32)
        return cls(mean, np.where(std > 1e-6, std, 1.0).astype(np.float32))

    def apply(self, values: F32) -> F32:
        return ((values - self.mean) / self.std).astype(np.float32)


@dataclass(frozen=True)
class Normalization:
    """Statistics from the training split only (README §7.1), saved with the model."""

    weather: Standardizer
    clim: Standardizer
    static: Standardizer
    crops: Standardizer

    def save(self, path: Path) -> None:
        payload = {
            name: {"mean": s.mean.tolist(), "std": s.std.tolist()}
            for name, s in (
                ("weather", self.weather), ("clim", self.clim),
                ("static", self.static), ("crops", self.crops),
            )
        }  # fmt: skip
        payload["channels"] = {
            "weather": list(WEATHER_CHANNELS),
            "clim": list(CLIM_CHANNELS),
            "static": list(STATIC_FEATURES),
        }
        path.write_text(json.dumps(payload, indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Normalization":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw["channels"]["weather"] != list(WEATHER_CHANNELS) or raw["channels"][
            "static"
        ] != list(STATIC_FEATURES):
            raise ValueError("normalization was saved for different input channels")

        def standardizer(name: str) -> Standardizer:
            return Standardizer(
                np.array(raw[name]["mean"], dtype=np.float32),
                np.array(raw[name]["std"], dtype=np.float32),
            )

        return cls(
            standardizer("weather"),
            standardizer("clim"),
            standardizer("static"),
            standardizer("crops"),
        )


@dataclass(frozen=True)
class SiteDateInputs:
    """One plot on one sowing date, ready for the network (channels first)."""

    weather: F32  # [len(WEATHER_CHANNELS), HISTORY_DAYS]
    clim: F32  # [len(CLIM_CHANNELS), AHEAD_DAYS]
    static: F32  # [len(STATIC_FEATURES)]


def site_date_inputs(
    weather_history: F32, clim_ahead: F32, site: F32, context: list[float], norm: Normalization
) -> SiteDateInputs:
    """weather_history [365, channels] ending the day before sowing; clim_ahead [210, ≥6]."""
    if weather_history.shape != (HISTORY_DAYS, len(WEATHER_CHANNELS)):
        raise ValueError(f"weather history must be {HISTORY_DAYS} x {len(WEATHER_CHANNELS)}")
    if clim_ahead.shape[0] != AHEAD_DAYS:
        raise ValueError(f"climatology ahead must cover {AHEAD_DAYS} days")
    static = np.concatenate([site, np.array(context, dtype=np.float32)])
    return SiteDateInputs(
        weather=norm.weather.apply(transform_weather(weather_history)).T.copy(),
        clim=norm.clim.apply(transform_clim(clim_ahead)).T.copy(),
        static=norm.static.apply(static),
    )
