"""Stages `download` and `clean`: public data in, the cleaned dataset out (README §4-§5)."""

import json
import logging
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import date

import numpy as np
import numpy.typing as npt

from fieldpilot_planner.clean.climatology import leave_one_out
from fieldpilot_planner.clean.et0 import (
    hargreaves,
    penman_monteith,
    radiation_from_temperature,
    saturation_vapour_pressure,
)
from fieldpilot_planner.clean.quality import clean_values, elevation_offset_c
from fieldpilot_planner.clean.soil import mean_between
from fieldpilot_planner.config import PipelineConfig
from fieldpilot_planner.crops import MAX_CYCLE_DAYS, CropCard
from fieldpilot_planner.dataset import CleanDataset
from fieldpilot_planner.features import WEATHER_CHANNELS
from fieldpilot_planner.paths import Paths
from fieldpilot_planner.points import Point
from fieldpilot_planner.sources.datos_gov import fetch_eva
from fieldpilot_planner.sources.http import CachedHttp
from fieldpilot_planner.sources.oni import fetch_oni
from fieldpilot_planner.sources.power import PowerSeries, fetch_power
from fieldpilot_planner.sources.soilgrids import (
    PROPERTIES,
    SoilGridsRasters,
    SoilProfile,
    load_profile,
    save_profile,
)

log = logging.getLogger(__name__)
F32 = npt.NDArray[np.float32]
POWER_WORKERS = 4
REQUIRED = ("t2m", "tmax", "tmin", "rain", "rh", "wind", "et0", "gwetroot")


def http_for(paths: Paths) -> CachedHttp:
    return CachedHttp(paths.raw / "http")


SOIL_MARGIN_DEG = 0.5


def soil_bounds(points: Sequence[Point]) -> tuple[float, float, float, float]:
    lats, lons = [p.lat for p in points], [p.lon for p in points]
    m = SOIL_MARGIN_DEG
    return min(lats) - m, max(lats) + m, min(lons) - m, max(lons) + m


def download(
    paths: Paths, points: Sequence[Point], crops: Sequence[CropCard], config: PipelineConfig
) -> None:
    """Fetch everything into the cache; safe to interrupt and run again."""
    http = http_for(paths)
    soil_dir = paths.raw / "soil"
    soil_dir.mkdir(parents=True, exist_ok=True)

    def power_one(point: Point) -> None:
        fetch_power(http, point.lat, point.lon, config.first_day, config.last_day)
        log.info("POWER %s %s ok", point.id, point.name)

    def soil_all() -> None:
        rasters = SoilGridsRasters(paths.raw / "soilgrids", soil_bounds(points))
        coords = [(p.lat, p.lon) for p in points]
        for point, profile in zip(
            points, rasters.profiles(coords, config.soil_search_km), strict=True
        ):
            save_profile(soil_dir / f"{point.id}.json", profile)
            log.info("SoilGrids %s %s %s", point.id, point.name, "ok" if profile else "NO PROFILE")

    fetch_oni(http)
    eva = fetch_eva(http, [n for c in crops for n in c.eva_names])
    log.info("EVA: %d municipality-crop-year records", len(eva))
    with ThreadPoolExecutor(max_workers=POWER_WORKERS + 1) as pool:
        soil_job = pool.submit(soil_all)
        for job in [pool.submit(power_one, p) for p in points]:
            job.result()
        soil_job.result()


@dataclass(frozen=True)
class PointResult:
    weather: F32
    valid: npt.NDArray[np.bool_]
    site: F32
    profile: F32
    clim: F32
    report: dict[str, object]


def profile_array(profile: SoilProfile) -> npt.NDArray[np.float64]:
    """[layers, PROPERTIES] from a SoilGrids profile."""
    return np.array(
        [[profile.layers[p][layer] for p in PROPERTIES] for layer in range(6)], dtype=np.float64
    )


def site_vector(
    lat: float, lon: float, elevation_m: float, cell_elevation_m: float,
    profile: npt.NDArray[np.float64],
) -> F32:  # fmt: skip
    """The site features in features.SITE_FEATURES order."""
    return np.concatenate([
        [lat, lon, elevation_m, elevation_m - cell_elevation_m],
        mean_between(profile, 0, 30), mean_between(profile, 30, 60),
    ]).astype(np.float32)  # fmt: skip


def _load_profile(paths: Paths, point: Point) -> SoilProfile | None:
    return load_profile(paths.raw / "soil" / f"{point.id}.json")


def weather_channels(
    series: PowerSeries, point: Point, config: PipelineConfig, doy: npt.NDArray[np.float64]
) -> tuple[F32, dict[str, object]]:
    values = {k: v.copy() for k, v in series.values.items()}
    counts = clean_values(values, config.max_gap_days)
    offset = elevation_offset_c(
        point.elevation_m, series.cell_elevation_m, config.lapse_rate_c_per_km
    )
    t, tmax, tmin = (values[k] + offset for k in ("T2M", "T2M_MAX", "T2M_MIN"))
    estimated = ~np.isfinite(values["ALLSKY_SFC_SW_DWN"])
    radiation = np.where(
        estimated,
        radiation_from_temperature(tmax, tmin, point.lat, doy),
        values["ALLSKY_SFC_SW_DWN"],
    )
    ea = saturation_vapour_pressure(values["T2MDEW"])  # dewpoint not corrected (README §5 step 6)
    pm = penman_monteith(
        tmax, tmin, ea, values["WS2M"], radiation, point.lat, point.elevation_m, doy
    )
    et0 = np.where(estimated, hargreaves(tmax, tmin, point.lat, doy), pm)
    channels = {
        "t2m": t, "tmax": tmax, "tmin": tmin, "rain": values["PRECTOTCORR"], "rh": values["RH2M"],
        "wind": values["WS2M"], "radiation": radiation, "et0": et0, "gwetroot": values["GWETROOT"],
        "radiation_estimated": estimated.astype(np.float64),
    }  # fmt: skip
    stacked = np.stack([channels[c] for c in WEATHER_CHANNELS], axis=-1).astype(np.float32)
    report = {
        **asdict(counts),
        "cell_elevation_m": series.cell_elevation_m,
        "temperature_offset_c": round(offset, 2),
        "radiation_estimated_days": int(estimated.sum()),
    }
    return stacked, report


def clean_point(
    paths: Paths, point: Point, config: PipelineConfig, label_years: range
) -> PointResult | str:
    """The cleaned arrays of one point, or the reason it is excluded."""
    http = http_for(paths)
    series = fetch_power(http, point.lat, point.lon, config.first_day, config.last_day)
    if series.days[0] != config.first_day or series.days[-1] != config.last_day:
        return "POWER series does not cover the configured period"
    profile = _load_profile(paths, point)
    if profile is None:
        return "no SoilGrids pixel with every layer within the search radius"
    doy = np.array([d.timetuple().tm_yday for d in series.days], dtype=np.float64)
    weather, report = weather_channels(series, point, config, doy)
    index = {c: i for i, c in enumerate(WEATHER_CHANNELS)}
    valid = np.all(np.isfinite(weather[:, [index[c] for c in REQUIRED]]), axis=1)
    masked = 1 - float(valid.mean())
    if masked > config.max_masked_fraction:
        return f"{masked:.1%} of days masked (limit {config.max_masked_fraction:.0%})"
    profile_arr = profile_array(profile)
    site = site_vector(
        point.lat, point.lon, point.elevation_m, series.cell_elevation_m, profile_arr
    )

    def col(channel: str) -> npt.NDArray[np.float64]:
        return weather[:, index[channel]].astype(np.float64)

    clim = leave_one_out(
        col("t2m"), col("rain"), col("tmax"), col("tmin"), col("et0"),
        config.first_day, config.baseline_years, label_years, config.smoothing_days,
    )  # fmt: skip
    report |= {"masked_fraction": round(masked, 4), "soil_moved_km": _moved_km(point, profile)}
    return PointResult(
        np.where(np.isfinite(weather), weather, 0.0).astype(np.float32),
        valid,
        site,
        profile_arr.astype(np.float32),
        clim,
        report,
    )


def _moved_km(point: Point, profile: SoilProfile) -> float:
    dlat = (profile.lat - point.lat) * 111.32
    dlon = (profile.lon - point.lon) * 111.32 * np.cos(np.radians(point.lat))
    return round(float(np.hypot(dlat, dlon)), 1)


def label_years(config: PipelineConfig) -> range:
    last_sowing_year = date.fromordinal(config.last_day.toordinal() - MAX_CYCLE_DAYS).year
    return range(config.first_sowing.year, last_sowing_year + 1)


def clean(paths: Paths, points: Sequence[Point], config: PipelineConfig) -> CleanDataset:
    years = label_years(config)
    kept: list[tuple[Point, PointResult]] = []
    report: dict[str, object] = {}
    for point in points:
        result = clean_point(paths, point, config, years)
        if isinstance(result, str):
            log.warning("excluded %s %s: %s", point.id, point.name, result)
            report[point.id] = {"name": point.name, "excluded": result}
            continue
        kept.append((point, result))
        report[point.id] = {"name": point.name, **result.report}
    paths.clean.mkdir(parents=True, exist_ok=True)
    (paths.clean / "quality_report.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    oni = fetch_oni(http_for(paths))
    months = sorted(oni)
    log.info("clean: %d points kept, %d excluded", len(kept), len(points) - len(kept))
    return CleanDataset(
        point_ids=np.array([p.id for p, _ in kept]),
        departments=np.array([p.department for p, _ in kept]),
        municipalities=np.array([p.municipality for p, _ in kept]),
        day0=config.first_day,
        weather=np.stack([r.weather for _, r in kept]),
        valid=np.stack([r.valid for _, r in kept]),
        site=np.stack([r.site for _, r in kept]),
        soil_profile=np.stack([r.profile for _, r in kept]),
        lat=np.array([p.lat for p, _ in kept], dtype=np.float32),
        oni_months=np.array([y * 12 + m - 1 for y, m in months], dtype=np.int32),
        oni_values=np.array([oni[k] for k in months], dtype=np.float32),
        clim_years=np.array(list(years), dtype=np.int32),
        clim=np.stack([r.clim for _, r in kept]),
    )
