"""`python -m fieldpilot_planner.site`: build one plot's site snapshot (D081).

Needs the network and the `data` extra (rasterio). The backend reads the
JSON it writes; nothing in the backend downloads data.
"""

import argparse
import logging
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np

from fieldpilot_planner.build import REQUIRED, http_for, profile_array, weather_channels
from fieldpilot_planner.clean.climatology import served_climatology
from fieldpilot_planner.config import PipelineConfig, load_pipeline
from fieldpilot_planner.features import WEATHER_CHANNELS
from fieldpilot_planner.paths import Paths
from fieldpilot_planner.points import Point
from fieldpilot_planner.serving import SNAPSHOT_WEATHER_DAYS, SiteSnapshot
from fieldpilot_planner.sources.elevation import fetch_elevations
from fieldpilot_planner.sources.oni import fetch_oni
from fieldpilot_planner.sources.power import fetch_power
from fieldpilot_planner.sources.soilgrids import SoilGridsRasters

log = logging.getLogger(__name__)
SOIL_MARGIN_DEG = 0.1  # the rasters are cropped to the plot and this margin


def build_snapshot(
    paths: Paths,
    config: PipelineConfig,
    lat: float,
    lon: float,
    elevation_m: float | None,
    today: date,
) -> SiteSnapshot:
    """Weather from the baseline's first year to the latest complete day, soil, ONI."""
    http = http_for(paths)
    first = date(config.baseline_years.first, 1, 1)
    series = fetch_power(http, lat, lon, first, today - timedelta(days=1))
    elevation = elevation_m if elevation_m is not None else fetch_elevations(http, [(lat, lon)])[0]
    point = Point("site", "", "", "site", lat, lon, elevation, 0.0)
    doy = np.array([d.timetuple().tm_yday for d in series.days], dtype=np.float64)
    weather, _ = weather_channels(series, point, config, doy)
    index = {c: i for i, c in enumerate(WEATHER_CHANNELS)}
    valid = np.all(np.isfinite(weather[:, [index[c] for c in REQUIRED]]), axis=1)
    last = int(np.flatnonzero(valid)[-1])  # recent POWER days arrive late: trim them

    def column(channel: str) -> np.ndarray:
        return weather[: last + 1, index[channel]].astype(np.float64)

    clim = served_climatology(
        column("t2m"), column("rain"), column("tmax"), column("tmin"), column("et0"),
        first, config.baseline_years, config.smoothing_days,
    )  # fmt: skip
    start = max(0, last + 1 - SNAPSHOT_WEATHER_DAYS)
    kept = weather[start : last + 1]
    return SiteSnapshot(
        lat=lat,
        lon=lon,
        elevation_m=elevation,
        cell_elevation_m=series.cell_elevation_m,
        soil_profile=_soil(paths, config, lat, lon).astype(np.float32),
        climatology=clim,
        weather_first_day=series.days[start],
        weather=np.where(np.isfinite(kept), kept, 0.0).astype(np.float32),
        valid=valid[start : last + 1],
        oni=fetch_oni(http),
        built_on=today,
    )


def _soil(paths: Paths, config: PipelineConfig, lat: float, lon: float) -> np.ndarray:
    m = SOIL_MARGIN_DEG
    rasters = SoilGridsRasters(paths.raw / "soilgrids", (lat - m, lat + m, lon - m, lon + m))
    profile = rasters.profiles([(lat, lon)], config.soil_search_km)[0]
    if profile is None:
        raise SystemExit(f"no SoilGrids pixel within {config.soil_search_km} km of the plot")
    return profile_array(profile)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fieldpilot_planner.site", description=__doc__)
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--elevation", type=float, help="metres; Open-Meteo when omitted")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])
    paths = Paths()
    config = load_pipeline(paths.configs / "pipeline.yaml")
    today = datetime.now(UTC).date()
    snapshot = build_snapshot(paths, config, args.lat, args.lon, args.elevation, today)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(snapshot.to_json(), encoding="utf-8", newline="\n")
    log.info("site snapshot %s: weather to %s", args.out, snapshot.last_day.isoformat())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
