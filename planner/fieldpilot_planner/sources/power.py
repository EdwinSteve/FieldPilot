"""NASA POWER daily point data (configs/sources.yaml: power)."""

from dataclasses import dataclass
from datetime import date

import numpy as np
import numpy.typing as npt

from fieldpilot_planner.sources.http import CachedHttp, build_url

POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETERS = (
    "T2M", "T2M_MAX", "T2M_MIN", "T2MDEW", "RH2M",
    "PRECTOTCORR", "WS2M", "ALLSKY_SFC_SW_DWN", "GWETROOT",
)  # fmt: skip
FILL_VALUE = -999.0


@dataclass(frozen=True)
class PowerSeries:
    days: tuple[date, ...]
    values: dict[str, npt.NDArray[np.float64]]  # NaN where POWER has its fill value
    cell_elevation_m: float


def power_url(lat: float, lon: float, first: date, last: date) -> str:
    return build_url(
        POWER_URL,
        {
            "parameters": ",".join(PARAMETERS),
            "community": "AG",
            "latitude": f"{lat:.4f}",
            "longitude": f"{lon:.4f}",
            "start": first.strftime("%Y%m%d"),
            "end": last.strftime("%Y%m%d"),
            "format": "JSON",
        },
    )


def fetch_power(http: CachedHttp, lat: float, lon: float, first: date, last: date) -> PowerSeries:
    payload = http.get_json(power_url(lat, lon, first, last))
    params = payload["properties"]["parameter"]
    keys = sorted(params[PARAMETERS[0]])
    days = tuple(date(int(k[:4]), int(k[4:6]), int(k[6:])) for k in keys)
    values: dict[str, npt.NDArray[np.float64]] = {}
    for name in PARAMETERS:
        series = np.array([params[name][k] for k in keys], dtype=np.float64)
        series[series <= FILL_VALUE] = np.nan
        values[name] = series
    return PowerSeries(days, values, float(payload["geometry"]["coordinates"][2]))
