"""Soil profile summaries: depth-weighted means down to a depth (README §5 step 10)."""

import numpy as np
import numpy.typing as npt

from fieldpilot_planner.sources.soilgrids import LAYER_BOUNDS_CM, PROPERTIES

Array = npt.NDArray[np.float64]


def depth_weights(top_cm: float, bottom_cm: float) -> Array:
    """Thickness of each SoilGrids layer inside [top, bottom], normalised to sum 1."""
    overlap = np.array([max(0.0, min(bottom_cm, b) - max(top_cm, t)) for t, b in LAYER_BOUNDS_CM])
    if overlap.sum() <= 0:
        raise ValueError(f"no soil layer between {top_cm} and {bottom_cm} cm")
    return np.asarray(overlap / overlap.sum())


def mean_between(profile: Array, top_cm: float, bottom_cm: float) -> Array:
    """profile [..., layers, properties] -> [..., properties]."""
    weights = depth_weights(top_cm, bottom_cm)
    return np.asarray(np.einsum("...lp,l->...p", profile, weights))


def total_available_water_mm(profile: Array, root_depth_m: float) -> Array:
    """FAO-56 Eq. 82: TAW = 1000 (θFC - θWP) Zr, with θ from SoilGrids wv0033 and wv1500 (% vol)."""
    depth_cm = min(root_depth_m * 100, LAYER_BOUNDS_CM[-1][1])
    means = mean_between(profile, 0, depth_cm)
    fc = means[..., PROPERTIES.index("wv0033")]
    wp = means[..., PROPERTIES.index("wv1500")]
    # Floor of 1 % volume: SoilGrids always has θ33 > θ1500; this only guards division by zero.
    return np.asarray(np.maximum(fc - wp, 1.0) / 100 * 1000 * root_depth_m)
