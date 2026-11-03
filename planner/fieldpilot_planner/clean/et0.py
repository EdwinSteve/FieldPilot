"""Reference evapotranspiration, FAO-56 (Allen et al., 1998), vectorised over days.

Equation numbers refer to FAO-56. Inputs are daily arrays; `doy` is the day of year.
"""

import numpy as np
import numpy.typing as npt

Array = npt.NDArray[np.float64]
SIGMA = 4.903e-9  # Stefan-Boltzmann, MJ K-4 m-2 day-1


def saturation_vapour_pressure(t_c: Array) -> Array:
    """Eq. 11, kPa."""
    return np.asarray(0.6108 * np.exp(17.27 * t_c / (t_c + 237.3)))


def extraterrestrial_radiation(lat_deg: float, doy: Array) -> Array:
    """Ra, Eqs. 21-25, MJ m-2 day-1."""
    phi = np.radians(lat_deg)
    dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)
    delta = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1.0, 1.0))
    return np.asarray(
        24 * 60 / np.pi * 0.0820 * dr
        * (ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws))
    )  # fmt: skip


def penman_monteith(
    tmax: Array, tmin: Array, ea: Array, u2: Array, rs: Array,
    lat_deg: float, elevation_m: float, doy: Array,
) -> Array:  # fmt: skip
    """Eq. 6 with G = 0 for daily steps, mm/day."""
    tmean = (tmax + tmin) / 2
    pressure = 101.3 * ((293 - 0.0065 * elevation_m) / 293) ** 5.26  # Eq. 7
    gamma = 0.000665 * pressure  # Eq. 8
    es = (saturation_vapour_pressure(tmax) + saturation_vapour_pressure(tmin)) / 2  # Eq. 12
    slope = 4098 * saturation_vapour_pressure(tmean) / (tmean + 237.3) ** 2  # Eq. 13
    ra = extraterrestrial_radiation(lat_deg, doy)
    rso = (0.75 + 2e-5 * elevation_m) * ra  # Eq. 37
    rns = 0.77 * rs  # Eq. 38, albedo 0.23
    relative = np.clip(rs / np.where(rso > 0, rso, np.nan), 0.0, 1.0)
    rnl = (
        SIGMA * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2
        * (0.34 - 0.14 * np.sqrt(np.maximum(ea, 0.0)))
        * (1.35 * relative - 0.35)
    )  # Eq. 39  # fmt: skip
    rn = rns - rnl
    numerator = 0.408 * slope * rn + gamma * 900 / (tmean + 273) * u2 * (es - ea)
    return np.asarray(np.maximum(numerator / (slope + gamma * (1 + 0.34 * u2)), 0.0))


def hargreaves(tmax: Array, tmin: Array, lat_deg: float, doy: Array) -> Array:
    """Eq. 52, mm/day: the fallback when radiation is missing."""
    ra = extraterrestrial_radiation(lat_deg, doy)
    tmean = (tmax + tmin) / 2
    return np.asarray(
        np.maximum(
            0.0023 * (tmean + 17.8) * np.sqrt(np.maximum(tmax - tmin, 0.0)) * 0.408 * ra, 0.0
        )
    )


def radiation_from_temperature(tmax: Array, tmin: Array, lat_deg: float, doy: Array) -> Array:
    """Eq. 50 with kRs = 0.16 (interior location), MJ m-2 day-1."""
    return np.asarray(
        0.16 * np.sqrt(np.maximum(tmax - tmin, 0.0)) * extraterrestrial_radiation(lat_deg, doy)
    )
