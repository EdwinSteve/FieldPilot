"""Leave-one-year-out daily climatology (README §5 step 11).

For each labelled year, the climatology of a point is the mean, p10 and p90
over the baseline years **without that year**, of a centred moving mean, by
day of year. It is the only input that describes the future, and it never
contains the year being labelled.
"""

from datetime import date, timedelta

import numpy as np
import numpy.typing as npt

from fieldpilot_planner.config import YearSpan

Array = npt.NDArray[np.float64]
DOY = 366
# Output order: the first six are network inputs (features.CLIM_CHANNELS).
CLIM_OUTPUTS = (
    "t_mean", "t_p10", "t_p90", "rain_mean", "rain_p10", "rain_p90",
    "tmax_mean", "tmin_mean", "et0_mean",
)  # fmt: skip


def moving_mean(series: Array, window: int) -> Array:
    """Centred moving mean that ignores NaN; NaN only where the whole window is missing."""
    valid = np.isfinite(series)
    kernel = np.ones(window)
    sums = np.convolve(np.where(valid, series, 0.0), kernel, mode="same")
    counts = np.convolve(valid.astype(float), kernel, mode="same")
    return np.where(counts > 0, sums / np.maximum(counts, 1), np.nan)


def by_day_of_year(smoothed: Array, day0: date, years: range) -> Array:
    """[year, 366]: day 366 repeats day 365 in non-leap years."""
    out = np.full((len(years), DOY), np.nan)
    for i, year in enumerate(years):
        start = (date(year, 1, 1) - day0).days
        length = (date(year + 1, 1, 1) - date(year, 1, 1)).days
        block = smoothed[start : start + length]
        out[i, :length] = block
        if length == DOY - 1:
            out[i, DOY - 1] = block[-1]
    return out


def leave_one_out(
    t: Array, rain: Array, tmax: Array, tmin: Array, et0: Array,
    day0: date, baseline: YearSpan, label_years: range, window: int,
) -> npt.NDArray[np.float32]:  # fmt: skip
    """[label year, 366, len(CLIM_OUTPUTS)] for one point."""
    base_years = range(baseline.first, baseline.last + 1)
    tables = _tables(t, rain, tmax, tmin, et0, day0, baseline, window)
    out = np.empty((len(label_years), DOY, len(CLIM_OUTPUTS)), dtype=np.float32)
    for i, year in enumerate(label_years):
        out[i] = _statistics(tables, np.array([y != year for y in base_years]))
    return out


def served_climatology(
    t: Array, rain: Array, tmax: Array, tmin: Array, et0: Array,
    day0: date, baseline: YearSpan, window: int,
) -> npt.NDArray[np.float32]:  # fmt: skip
    """[366, len(CLIM_OUTPUTS)] over every baseline year: what a plot is served with (D081)."""
    tables = _tables(t, rain, tmax, tmin, et0, day0, baseline, window)
    return _statistics(tables, np.ones(baseline.last - baseline.first + 1, dtype=bool))


def _tables(
    t: Array, rain: Array, tmax: Array, tmin: Array, et0: Array,
    day0: date, baseline: YearSpan, window: int,
) -> dict[str, Array]:  # fmt: skip
    base_years = range(baseline.first, baseline.last + 1)
    return {
        name: by_day_of_year(moving_mean(series, window), day0, base_years)
        for name, series in (("t", t), ("rain", rain), ("tmax", tmax), ("tmin", tmin), ("et0", et0))
    }


def _statistics(tables: dict[str, Array], keep: npt.NDArray[np.bool_]) -> npt.NDArray[np.float32]:
    t_tab, rain_tab = tables["t"][keep], tables["rain"][keep]
    return np.stack(
        [
            np.nanmean(t_tab, 0),
            np.nanpercentile(t_tab, 10, 0), np.nanpercentile(t_tab, 90, 0),
            np.nanmean(rain_tab, 0), np.nanpercentile(rain_tab, 10, 0),
            np.nanpercentile(rain_tab, 90, 0),
            np.nanmean(tables["tmax"][keep], 0), np.nanmean(tables["tmin"][keep], 0),
            np.nanmean(tables["et0"][keep], 0),
        ],
        axis=-1,
    ).astype(np.float32)  # fmt: skip


def day_of_year_index(day: date) -> int:
    """0-based index into the 366 columns; 31 Dec of a non-leap year maps to 364."""
    return (day - date(day.year, 1, 1)).days


def dates_from(day0: date, count: int) -> list[date]:
    return [day0 + timedelta(days=i) for i in range(count)]
