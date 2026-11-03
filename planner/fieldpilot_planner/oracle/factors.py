"""Yield factors from published crop requirements (README §6)."""

import numpy as np
import numpy.typing as npt

Array = npt.NDArray[np.float64]


def trapezoid(x: Array, low: float, opt_low: float, opt_high: float, high: float) -> Array:
    """ECOCROP suitability: 0 at or past the absolute limits, 1 in the optimal range."""
    rising = (x - low) / max(opt_low - low, 1e-9)
    falling = (high - x) / max(high - opt_high, 1e-9)
    return np.asarray(np.clip(np.minimum(rising, falling), 0.0, 1.0))


def water_factor(eta: Array, etc: Array, ky: float) -> Array:
    """FAO-33 seasonal yield response: 1 - Ya/Ym = Ky (1 - ETa/ETc), clipped to [0, 1]."""
    ratio = np.where(etc > 0, eta / np.maximum(etc, 1e-9), 1.0)
    return np.asarray(np.clip(1 - ky * (1 - ratio), 0.0, 1.0))
