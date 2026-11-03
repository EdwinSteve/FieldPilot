"""The network's outputs and the oracle's outcomes, decoded the same way (no torch).

Evaluation and serving both read predictions through this module.
"""

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

F32 = npt.NDArray[np.float32]


@dataclass(frozen=True)
class Predictions:
    """[N, C, 3] quantiles, [N, C] probability, [N, C, 3] irrigation in mm."""

    rel_yield: F32
    success: F32
    irrigation_mm: F32


def from_network(raw: F32) -> Predictions:
    """raw [N, C, 9] in the layout of models/net.py."""
    return Predictions(
        rel_yield=np.clip(raw[..., 0:3], 0.0, 1.0),
        success=(1 / (1 + np.exp(-raw[..., 3]))).astype(np.float32),
        irrigation_mm=np.maximum(np.expm1(raw[..., 4:7]), 0.0),
    )


def from_outcomes(outcomes: F32) -> Predictions:
    """Oracle outcomes [N, C, len(LABELS)]: a point estimate, all three quantiles equal."""
    return Predictions(
        rel_yield=np.repeat(outcomes[..., 0:1], 3, axis=-1),
        success=outcomes[..., 1],
        irrigation_mm=np.repeat(outcomes[..., 2:3], 3, axis=-1),
    )


def stress_days(raw: F32, cycle_days: F32) -> tuple[F32, F32]:
    """Heat and cold days [N, C] from the network's cycle fractions."""
    days = np.clip(raw[..., 7:9], 0.0, 1.0) * cycle_days[None, :, None]
    return days[..., 0].astype(np.float32), days[..., 1].astype(np.float32)
