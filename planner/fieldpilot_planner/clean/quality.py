"""Quality steps 1-5 and 6 of README §5: ranges, consistency, gaps and the elevation correction."""

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

Array = npt.NDArray[np.float64]

# Physical ranges (README §5 step 2); a value outside becomes missing.
RANGES: dict[str, tuple[float, float]] = {
    "T2M": (-10.0, 50.0),
    "T2M_MAX": (-10.0, 50.0),
    "T2M_MIN": (-10.0, 50.0),
    "T2MDEW": (-30.0, 40.0),
    "RH2M": (0.0, 100.0),
    "PRECTOTCORR": (0.0, 400.0),
    "WS2M": (0.0, 40.0),
    "ALLSKY_SFC_SW_DWN": (0.0, 45.0),
    "GWETROOT": (0.0, 1.0),
}
NOT_INTERPOLATED = frozenset({"PRECTOTCORR"})  # rain is never invented


@dataclass(frozen=True)
class QualityCounts:
    out_of_range: int
    inconsistent_days: int
    interpolated: int


def apply_ranges(values: dict[str, Array]) -> int:
    count = 0
    for name, (low, high) in RANGES.items():
        series = values[name]
        bad = (series < low) | (series > high)
        count += int(bad.sum())
        series[bad] = np.nan
    return count


def apply_consistency(values: dict[str, Array]) -> int:
    t, tmax, tmin = values["T2M"], values["T2M_MAX"], values["T2M_MIN"]
    bad = (tmin > t) | (t > tmax)
    for series in (t, tmax, tmin):
        series[bad] = np.nan
    return int(bad.sum())


def fill_short_gaps(series: Array, max_gap: int) -> int:
    """Linear interpolation inside gaps of at most `max_gap` days, in place; edges stay missing."""
    missing = np.isnan(series)
    if not missing.any():
        return 0
    filled = 0
    idx = np.flatnonzero(missing)
    runs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
    for run in runs:
        start, end = int(run[0]), int(run[-1])
        if len(run) > max_gap or start == 0 or end == len(series) - 1:
            continue
        before, after = series[start - 1], series[end + 1]
        steps = np.arange(1, len(run) + 1) / (len(run) + 1)
        series[start : end + 1] = before + (after - before) * steps
        filled += len(run)
    return filled


def clean_values(values: dict[str, Array], max_gap: int) -> QualityCounts:
    """Steps 2-4, in place."""
    out_of_range = apply_ranges(values)
    inconsistent = apply_consistency(values)
    interpolated = sum(
        fill_short_gaps(series, max_gap)
        for name, series in values.items()
        if name not in NOT_INTERPOLATED
    )
    return QualityCounts(out_of_range, inconsistent, interpolated)


def elevation_offset_c(point_m: float, cell_m: float, lapse_c_per_km: float) -> float:
    """Step 6: add this to POWER temperatures (positive when the plot is below the cell)."""
    return lapse_c_per_km * (point_m - cell_m) / 1000
