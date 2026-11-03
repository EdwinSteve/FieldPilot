"""Labels per point, sowing date and crop: the oracle on real weather and on climatology (B0)."""

import logging
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import numpy as np
import numpy.typing as npt

from fieldpilot_planner.clean.soil import mean_between, total_available_water_mm
from fieldpilot_planner.config import PipelineConfig
from fieldpilot_planner.crops import MAX_CYCLE_DAYS, CropCard
from fieldpilot_planner.dataset import CleanDataset
from fieldpilot_planner.features import HISTORY_DAYS, WEATHER_CHANNELS
from fieldpilot_planner.oracle.factors import trapezoid, water_factor
from fieldpilot_planner.oracle.water_balance import run_season
from fieldpilot_planner.sources.soilgrids import PROPERTIES

log = logging.getLogger(__name__)
Array = npt.NDArray[np.float64]

LABELS = ("rel_yield", "success", "irrigation_mm", "heat_days", "cold_days")
FACTORS = ("water", "temperature", "ph")
CLIM_INDEX = {"t": 0, "rain": 3, "tmax": 6, "tmin": 7, "et0": 8}  # climatology.CLIM_OUTPUTS
W = {c: i for i, c in enumerate(WEATHER_CHANNELS)}


@dataclass(frozen=True)
class CycleWeather:
    """[S, cycle days] each, plus the spin-up before sowing."""

    t: Array
    tmin: Array
    rain: Array
    et0: Array
    spin_rain: Array
    spin_et0: Array


@dataclass(frozen=True)
class Outcome:
    labels: Array  # [S, len(LABELS)]
    factors: Array  # [S, len(FACTORS)]


def simulate(
    weather: CycleWeather, crop: CropCard, taw: float, soil_ph: float, success_threshold: float
) -> Outcome:
    """The oracle for one crop on one point, over all sowing dates at once."""
    kc = crop.kc_curve().astype(np.float64)
    spin = run_season(
        weather.spin_rain, weather.spin_et0 * crop.kc_ini, taw, crop.depletion_p,
        np.full(weather.t.shape[0], 0.5 * taw), irrigate=False,
    )  # fmt: skip
    etc = weather.et0 * kc[None, :]
    rainfed = run_season(
        weather.rain, etc, taw, crop.depletion_p, spin.final_depletion_mm, irrigate=False
    )
    irrigated = run_season(
        weather.rain, etc, taw, crop.depletion_p, spin.final_depletion_mm, irrigate=True
    )

    water = water_factor(rainfed.eta_mm, rainfed.etc_mm, crop.ky)
    temperature = trapezoid(
        weather.t, crop.tmin_c, crop.topt_min_c, crop.topt_max_c, crop.tmax_c
    ).mean(axis=1)
    killed = (weather.tmin < crop.kill_c).any(axis=1)
    ph = float(
        trapezoid(np.array([soil_ph]), crop.ph_min, crop.ph_opt_min, crop.ph_opt_max, crop.ph_max)[
            0
        ]
    )
    rel_yield = water * temperature * ph * ~killed
    labels = np.stack(
        [
            rel_yield,
            (rel_yield >= success_threshold).astype(np.float64),
            irrigated.irrigation_mm,
            (weather.t > crop.topt_max_c).sum(axis=1).astype(np.float64),
            (weather.t < crop.topt_min_c).sum(axis=1).astype(np.float64),
        ],
        axis=1,
    )
    factors = np.stack([water, temperature, np.full_like(water, ph)], axis=1)
    return Outcome(labels, factors)


def sowing_indices(data: CleanDataset, config: PipelineConfig) -> npt.NDArray[np.int64]:
    first = (config.first_sowing - data.day0).days
    if first < HISTORY_DAYS:
        raise ValueError("first sowing leaves less than a year of history")
    last_year = int(data.clim_years[-1])
    candidates = np.arange(first, data.days - MAX_CYCLE_DAYS, config.sowing_step_days)
    return np.array([i for i in candidates if data.day(int(i)).year <= last_year], dtype=np.int64)


def valid_samples(data: CleanDataset, sow: npt.NDArray[np.int64]) -> npt.NDArray[np.bool_]:
    """[P, S]: the year before sowing and the longest cycle after it are all valid days."""
    invalid = np.concatenate(
        [np.zeros((data.valid.shape[0], 1)), np.cumsum(~data.valid, axis=1)], axis=1
    )
    return np.asarray(invalid[:, sow + MAX_CYCLE_DAYS] - invalid[:, sow - HISTORY_DAYS] == 0)


def _real_weather(
    data: CleanDataset, p: int, sow: npt.NDArray[np.int64], days: int, spin: int
) -> CycleWeather:
    cycle = sow[:, None] + np.arange(days)[None, :]
    before = sow[:, None] + np.arange(-spin, 0)[None, :]
    w = data.weather[p].astype(np.float64)
    return CycleWeather(
        t=w[cycle, W["t2m"]], tmin=w[cycle, W["tmin"]], rain=w[cycle, W["rain"]],
        et0=w[cycle, W["et0"]], spin_rain=w[before, W["rain"]], spin_et0=w[before, W["et0"]],
    )  # fmt: skip


def _climatology_weather(
    data: CleanDataset, p: int, sow: npt.NDArray[np.int64], days: int, real: CycleWeather
) -> CycleWeather:
    """B0: the cycle sees the leave-one-year-out climatology; the spin-up is the real past."""
    sow_dates = [data.day(int(i)) for i in sow]
    year_idx = np.array([d.year - int(data.clim_years[0]) for d in sow_dates])
    doy0 = np.array([(d - d.replace(month=1, day=1)).days for d in sow_dates])
    doy = (doy0[:, None] + np.arange(days)[None, :]) % 366
    clim = data.clim[p].astype(np.float64)

    def pick(name: str) -> Array:
        return np.asarray(clim[year_idx[:, None], doy, CLIM_INDEX[name]])

    return CycleWeather(
        t=pick("t"), tmin=pick("tmin"), rain=pick("rain"), et0=pick("et0"),
        spin_rain=real.spin_rain, spin_et0=real.spin_et0,
    )  # fmt: skip


@dataclass(frozen=True)
class LabelSet:
    sow: npt.NDArray[np.int64]  # [S] day indices
    valid: npt.NDArray[np.bool_]  # [P, S]
    labels: npt.NDArray[np.float32]  # [P, S, C, len(LABELS)]
    factors: npt.NDArray[np.float32]  # [P, S, C, len(FACTORS)]
    b0: npt.NDArray[np.float32]  # [P, S, C, len(LABELS)]

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        np.savez(directory / "labels.npz", sow=self.sow, valid=self.valid, labels=self.labels,
                 factors=self.factors, b0=self.b0)  # fmt: skip

    @classmethod
    def load(cls, directory: Path) -> "LabelSet":
        with np.load(directory / "labels.npz") as f:
            return cls(f["sow"], f["valid"], f["labels"], f["factors"], f["b0"])


def build_labels(data: CleanDataset, crops: list[CropCard], config: PipelineConfig) -> LabelSet:
    sow = sowing_indices(data, config)
    shape = (data.weather.shape[0], len(sow), len(crops))
    labels = np.zeros((*shape, len(LABELS)), dtype=np.float32)
    factors = np.zeros((*shape, len(FACTORS)), dtype=np.float32)
    b0 = np.zeros((*shape, len(LABELS)), dtype=np.float32)
    ph_index = PROPERTIES.index("phh2o")
    for p in range(data.weather.shape[0]):
        profile = data.soil_profile[p].astype(np.float64)
        soil_ph = float(mean_between(profile, 0, 30)[ph_index])
        for c, crop in enumerate(crops):
            taw = float(total_available_water_mm(profile, crop.root_depth_m))
            real = _real_weather(data, p, sow, crop.cycle_days, config.spinup_days)
            outcome = simulate(real, crop, taw, soil_ph, config.success_rel_yield)
            labels[p, :, c], factors[p, :, c] = outcome.labels, outcome.factors
            clim = _climatology_weather(data, p, sow, crop.cycle_days, real)
            b0[p, :, c] = simulate(clim, crop, taw, soil_ph, config.success_rel_yield).labels
        log.info("labels %d/%d %s", p + 1, data.weather.shape[0], data.point_ids[p])
    return LabelSet(sow, valid_samples(data, sow), labels, factors, b0)


def sowing_years(data: CleanDataset, sow: npt.NDArray[np.int64]) -> npt.NDArray[np.int64]:
    return np.array([(data.day0 + timedelta(days=int(i))).year for i in sow], dtype=np.int64)
