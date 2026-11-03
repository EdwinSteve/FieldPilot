"""Serving: one plot's model inputs from its site snapshot (D081).

The backend calls this module with a trained bundle. It reuses the features,
the climatology layout and the oracle that training used, so a served plan
cannot drift from what the network learned. numpy only: no torch.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np
import numpy.typing as npt

from fieldpilot_planner.clean.climatology import CLIM_OUTPUTS, DOY, day_of_year_index
from fieldpilot_planner.clean.soil import mean_between, total_available_water_mm
from fieldpilot_planner.crops import CropCard, crop_matrix
from fieldpilot_planner.features import (
    AHEAD_DAYS,
    HISTORY_DAYS,
    WEATHER_CHANNELS,
    Normalization,
    context_vector,
    oni_known_at,
    prior_features,
    site_date_inputs,
)
from fieldpilot_planner.oracle.labels import CLIM_INDEX, LABELS, CycleWeather, W, simulate
from fieldpilot_planner.outputs import Predictions, from_network, from_outcomes, stress_days
from fieldpilot_planner.sources.soilgrids import LAYER_BOUNDS_CM, PROPERTIES

F32 = npt.NDArray[np.float32]
SNAPSHOT_FORMAT = 1
# Two years of daily weather: a plan may start up to a year before the snapshot's last day.
SNAPSHOT_WEATHER_DAYS = 2 * HISTORY_DAYS
OniTable = Mapping[tuple[int, int], float]


class IncompleteHistoryError(ValueError):
    """The snapshot has no complete year of weather before a sowing date."""


@dataclass(frozen=True)
class SiteSnapshot:
    """Everything the planner needs about one plot, built once by `fieldpilot_planner.site`."""

    lat: float
    lon: float
    elevation_m: float
    cell_elevation_m: float  # of the NASA POWER cell
    soil_profile: F32  # [len(LAYER_BOUNDS_CM), len(PROPERTIES)]
    climatology: F32  # [366, len(CLIM_OUTPUTS)], baseline years, by day of year
    weather_first_day: date
    weather: F32  # [days, len(WEATHER_CHANNELS)], cleaned; invalid days hold 0 as in training
    valid: npt.NDArray[np.bool_]  # [days]
    oni: OniTable  # (year, month the season ends) -> value
    built_on: date

    def __post_init__(self) -> None:
        if self.soil_profile.shape != (len(LAYER_BOUNDS_CM), len(PROPERTIES)):
            raise ValueError("soil profile must be layers x SoilGrids properties")
        if self.climatology.shape != (DOY, len(CLIM_OUTPUTS)):
            raise ValueError(f"climatology must be {DOY} x {len(CLIM_OUTPUTS)}")
        if self.weather.ndim != 2 or self.weather.shape[1] != len(WEATHER_CHANNELS):
            raise ValueError("weather must be days x WEATHER_CHANNELS")
        if self.valid.shape != (self.weather.shape[0],):
            raise ValueError("valid must have one flag per weather day")

    @property
    def last_day(self) -> date:
        return self.weather_first_day + timedelta(days=self.weather.shape[0] - 1)

    def site_features(self) -> F32:
        """The site features in features.SITE_FEATURES order."""
        profile = self.soil_profile.astype(np.float64)
        return np.concatenate([
            [self.lat, self.lon, self.elevation_m, self.elevation_m - self.cell_elevation_m],
            mean_between(profile, 0, 30), mean_between(profile, 30, 60),
        ]).astype(np.float32)  # fmt: skip

    def to_json(self) -> str:
        payload: dict[str, Any] = {
            "format": SNAPSHOT_FORMAT,
            "channels": {"weather": list(WEATHER_CHANNELS), "climatology": list(CLIM_OUTPUTS)},
            "lat": self.lat,
            "lon": self.lon,
            "elevation_m": self.elevation_m,
            "cell_elevation_m": self.cell_elevation_m,
            "soil_profile": np.round(self.soil_profile, 4).tolist(),
            "climatology": np.round(self.climatology, 4).tolist(),
            "weather_first_day": self.weather_first_day.isoformat(),
            "weather": np.round(self.weather, 4).tolist(),
            "valid": self.valid.astype(int).tolist(),
            "oni": [[y, m, v] for (y, m), v in sorted(self.oni.items())],
            "built_on": self.built_on.isoformat(),
        }
        return json.dumps(payload, separators=(",", ":"))

    @classmethod
    def from_json(cls, text: str) -> "SiteSnapshot":
        raw = json.loads(text)
        if raw.get("format") != SNAPSHOT_FORMAT:
            raise ValueError(f"site snapshot format must be {SNAPSHOT_FORMAT}")
        channels = raw["channels"]
        if channels["weather"] != list(WEATHER_CHANNELS) or channels["climatology"] != list(
            CLIM_OUTPUTS
        ):
            raise ValueError("site snapshot was built for different channels")
        return cls(
            lat=float(raw["lat"]),
            lon=float(raw["lon"]),
            elevation_m=float(raw["elevation_m"]),
            cell_elevation_m=float(raw["cell_elevation_m"]),
            soil_profile=np.array(raw["soil_profile"], dtype=np.float32),
            climatology=np.array(raw["climatology"], dtype=np.float32),
            weather_first_day=date.fromisoformat(raw["weather_first_day"]),
            weather=np.array(raw["weather"], dtype=np.float32),
            valid=np.array(raw["valid"], dtype=bool),
            oni={(int(y), int(m)): float(v) for y, m, v in raw["oni"]},
            built_on=date.fromisoformat(raw["built_on"]),
        )


@dataclass(frozen=True)
class SowingContext:
    """How one sowing date was served: what is known, and what had to be assumed."""

    sowing_date: date
    history_end: date  # the last day of weather the network read
    oni: float
    oni_latest_published: bool  # the season due before sowing is not out yet (D081)


@dataclass(frozen=True)
class ClimatologyPlan:
    """B0 for N sowing dates and C crops: the oracle run on the climatology ahead."""

    contexts: tuple[SowingContext, ...]
    b0: F32  # [N, C, len(LABELS)], in the oracle's own units
    cycle_days: F32  # [C]


@dataclass(frozen=True)
class PlanInputs:
    """The network's five inputs for N sowing dates and C crops, and the B0 behind its prior."""

    weather: F32  # [N, len(WEATHER_CHANNELS), HISTORY_DAYS]
    clim: F32  # [N, 6, AHEAD_DAYS]
    static: F32  # [N, len(STATIC_FEATURES)]
    crops: F32  # [C, len(CROP_FEATURES)], normalised
    prior: F32  # [N, C, 5]: B0 on the network's scale
    climatology: ClimatologyPlan


@dataclass(frozen=True)
class PlanOutputs:
    predictions: Predictions
    heat_days: F32  # [N, C]
    cold_days: F32  # [N, C]


def climatology_plan(
    snapshot: SiteSnapshot,
    sowing_dates: Sequence[date],
    crops: Sequence[CropCard],
    success_threshold: float,
    spinup_days: int,
) -> ClimatologyPlan:
    """B0 alone: what the backend serves when no adopted network is available."""
    if not sowing_dates:
        raise ValueError("at least one sowing date is needed")
    soil = _SoilFacts.of(snapshot, crops)
    windows = [_window(snapshot, day) for day in sowing_dates]
    b0 = np.stack([
        _b0(w, crops, soil, success_threshold, spinup_days) for w in windows
    ]).astype(np.float32)  # fmt: skip
    return ClimatologyPlan(
        contexts=tuple(w.context for w in windows),
        b0=b0,
        cycle_days=np.array([c.cycle_days for c in crops], dtype=np.float32),
    )


def plan_inputs(
    snapshot: SiteSnapshot,
    sowing_dates: Sequence[date],
    crops: Sequence[CropCard],
    norm: Normalization,
    success_threshold: float,
    spinup_days: int,
) -> PlanInputs:
    """Build the network's inputs for every sowing date, as training built them (README §7.1)."""
    climatology = climatology_plan(snapshot, sowing_dates, crops, success_threshold, spinup_days)
    site = snapshot.site_features()
    rows = []
    for day in sowing_dates:
        w = _window(snapshot, day)
        context = context_vector(w.context.oni, w.oni_trend, day)
        rows.append(site_date_inputs(w.history, w.clim_ahead, site, context, norm))
    return PlanInputs(
        weather=np.stack([r.weather for r in rows]),
        clim=np.stack([r.clim for r in rows]),
        static=np.stack([r.static for r in rows]),
        crops=norm.crops.apply(crop_matrix(list(crops))),
        prior=prior_features(climatology.b0, climatology.cycle_days),
        climatology=climatology,
    )


def decode_network(raw: F32, inputs: PlanInputs) -> PlanOutputs:
    """raw [N, C, 9] from the network (models/net.py)."""
    heat, cold = stress_days(raw, inputs.climatology.cycle_days)
    return PlanOutputs(from_network(raw), heat, cold)


def decode_b0(plan: ClimatologyPlan) -> PlanOutputs:
    """B0 as a plan: a point estimate, all three quantiles equal."""
    heat = plan.b0[..., LABELS.index("heat_days")]
    cold = plan.b0[..., LABELS.index("cold_days")]
    return PlanOutputs(from_outcomes(plan.b0), heat, cold)


@dataclass(frozen=True)
class _SoilFacts:
    taw_mm: tuple[float, ...]  # per crop, for its root depth
    ph: float

    @classmethod
    def of(cls, snapshot: SiteSnapshot, crops: Sequence[CropCard]) -> "_SoilFacts":
        profile = snapshot.soil_profile.astype(np.float64)
        ph = float(mean_between(profile, 0, 30)[PROPERTIES.index("phh2o")])
        taw = tuple(float(total_available_water_mm(profile, c.root_depth_m)) for c in crops)
        return cls(taw, ph)


@dataclass(frozen=True)
class _Window:
    """What is known on one sowing date: the year before it and the climatology ahead."""

    context: SowingContext
    oni_trend: float
    history: F32  # [HISTORY_DAYS, len(WEATHER_CHANNELS)]
    clim_ahead: F32  # [AHEAD_DAYS, len(CLIM_OUTPUTS)]


def _window(snapshot: SiteSnapshot, sowing: date) -> _Window:
    history_end = min(sowing - timedelta(days=1), snapshot.last_day)
    end = (history_end - snapshot.weather_first_day).days + 1
    start = end - HISTORY_DAYS
    if start < 0 or not snapshot.valid[start:end].all():
        raise IncompleteHistoryError(
            f"no complete year of weather before {sowing.isoformat()} in the site snapshot"
        )
    doy = (day_of_year_index(sowing) + np.arange(AHEAD_DAYS)) % DOY
    oni, trend, latest = _oni_at(snapshot.oni, sowing)
    return _Window(
        context=SowingContext(sowing, history_end, oni, latest),
        oni_trend=trend,
        history=snapshot.weather[start:end],
        clim_ahead=snapshot.climatology[doy],
    )


def _b0(
    window: _Window,
    crops: Sequence[CropCard],
    soil: _SoilFacts,
    success_threshold: float,
    spinup_days: int,
) -> F32:
    """[C, len(LABELS)]: the oracle per crop, spun up on the last days of real weather."""
    spin = window.history[-spinup_days:]
    return np.stack([
        simulate(_climatology_cycle(window.clim_ahead, spin, crop), crop, taw, soil.ph,
                 success_threshold).labels[0]
        for crop, taw in zip(crops, soil.taw_mm, strict=True)
    ]).astype(np.float32)  # fmt: skip


def _climatology_cycle(clim_ahead: F32, spin: F32, crop: CropCard) -> CycleWeather:
    """B0's weather: the climatology over the cycle, the real past for the spin-up."""
    cycle = clim_ahead[: crop.cycle_days].astype(np.float64)

    def pick(name: str) -> npt.NDArray[np.float64]:
        return cycle[None, :, CLIM_INDEX[name]]

    past = spin.astype(np.float64)
    return CycleWeather(
        t=pick("t"), tmin=pick("tmin"), rain=pick("rain"), et0=pick("et0"),
        spin_rain=past[None, :, W["rain"]], spin_et0=past[None, :, W["et0"]],
    )  # fmt: skip


def _oni_at(oni: OniTable, sowing: date) -> tuple[float, float, bool]:
    """The ONI known at sowing (features.oni_known_at); for a sowing too far ahead, the latest."""
    try:
        value, trend = oni_known_at(oni, sowing)
    except KeyError:
        year, month = max(oni)
        index = year * 12 + month - 1 - 3
        earlier = oni.get((index // 12, index % 12 + 1))
        if earlier is None:
            raise IncompleteHistoryError("the snapshot's ONI table is too short") from None
        return oni[(year, month)], oni[(year, month)] - earlier, True
    return value, trend, False
