"""FAO-56 root-zone water balance (Chapter 8), vectorised over sowing dates.

Every array is [S, days]: one row per sowing date. The loop runs over days;
all sowings advance together.
"""

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

Array = npt.NDArray[np.float64]


@dataclass(frozen=True)
class SeasonWater:
    eta_mm: Array  # [S] actual crop ET over the cycle
    etc_mm: Array  # [S] crop ET without water stress
    irrigation_mm: Array  # [S] zero for a rainfed run
    final_depletion_mm: Array  # [S]


def water_stress_coefficient(depletion: Array, taw: float, raw: float) -> Array:
    """Ks, FAO-56 Eq. 84: 1 while depletion <= RAW, then linear to 0 at TAW."""
    return np.asarray(
        np.where(depletion <= raw, 1.0, np.clip((taw - depletion) / (taw - raw), 0.0, 1.0))
    )


def run_season(
    rain: Array, etc: Array, taw: float, depletion_fraction: float,
    initial_depletion: Array, irrigate: bool,
) -> SeasonWater:  # fmt: skip
    """FAO-56 Eq. 85 with daily steps.

    Rain above the root zone's deficit leaves as runoff or deep percolation;
    the depletion stays within [0, TAW]. With `irrigate`, whenever the
    depletion at the start of a day exceeds RAW, irrigation refills the root
    zone to field capacity (README §6).
    """
    raw = depletion_fraction * taw
    depletion = initial_depletion.astype(np.float64, copy=True)
    eta = np.zeros(rain.shape[0])
    irrigation = np.zeros(rain.shape[0])
    for day in range(rain.shape[1]):
        if irrigate:
            applied = np.where(depletion > raw, depletion, 0.0)
            irrigation += applied
            depletion = depletion - applied
        actual = water_stress_coefficient(depletion, taw, raw) * etc[:, day]
        eta += actual
        depletion = np.clip(depletion - rain[:, day] + actual, 0.0, taw)
    return SeasonWater(eta, etc.sum(axis=1), irrigation, depletion)
