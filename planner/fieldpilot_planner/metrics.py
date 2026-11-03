"""Evaluation metrics (README §7.3). Pure NumPy, so they are tested without a GPU."""

import numpy as np
import numpy.typing as npt

QUANTILES = (0.1, 0.5, 0.9)
Array = npt.NDArray[np.floating]


def pinball(pred: Array, target: Array) -> float:
    """pred [..., 3] for QUANTILES; target [...]."""
    diff = target[..., None] - pred
    q = np.array(QUANTILES)
    return float(np.maximum(q * diff, (q - 1) * diff).mean())


def brier(prob: Array, outcome: Array) -> float:
    return float(((prob - outcome) ** 2).mean())


def expected_calibration_error(prob: Array, outcome: Array, bins: int = 10) -> float:
    prob, outcome = prob.ravel(), outcome.ravel()
    edges = np.linspace(0, 1, bins + 1)
    which = np.clip(np.digitize(prob, edges[1:-1]), 0, bins - 1)
    error = 0.0
    for b in range(bins):
        members = which == b
        if members.any():
            error += members.mean() * abs(prob[members].mean() - outcome[members].mean())
    return float(error)


def coverage(low: Array, high: Array, target: Array) -> float:
    return float(((target >= low) & (target <= high)).mean())


def ndcg_at_k(scores: Array, relevance: Array, k: int = 3) -> float:
    """Mean NDCG@k over rows: each row ranks the crops of one site-date."""
    discounts = 1 / np.log2(np.arange(2, k + 2))
    order = np.argsort(-scores, axis=1)[:, :k]
    ideal = np.sort(relevance, axis=1)[:, ::-1][:, :k]
    gained = np.take_along_axis(relevance, order, axis=1)
    dcg = (gained * discounts).sum(axis=1)
    idcg = (ideal * discounts).sum(axis=1)
    return float(np.where(idcg > 0, dcg / np.where(idcg > 0, idcg, 1), 1.0).mean())


def rank(values: Array) -> Array:
    """Ranks with ties averaged (Spearman needs them)."""
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values))
    ranks[order] = np.arange(len(values), dtype=float)
    sorted_values = values[order]
    start = 0
    for i in range(1, len(values) + 1):
        if i == len(values) or sorted_values[i] != sorted_values[start]:
            ranks[order[start:i]] = (start + i - 1) / 2
            start = i
    return ranks


def spearman(a: Array, b: Array) -> float:
    if len(a) < 3:
        return float("nan")
    ra, rb = rank(a), rank(b)
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def summary(
    yield_q: Array, success_p: Array, irrigation_q: Array,
    true_yield: Array, true_success: Array, true_irrigation: Array,
) -> dict[str, float]:  # fmt: skip
    """All arrays are [N, C] (quantile arrays [N, C, 3]); irrigation in mm."""
    return {
        "rel_yield_pinball": round(pinball(yield_q, true_yield), 5),
        "rel_yield_mae": round(float(np.abs(yield_q[..., 1] - true_yield).mean()), 5),
        "rel_yield_coverage_p10_p90": round(
            coverage(yield_q[..., 0], yield_q[..., 2], true_yield), 4
        ),
        "success_brier": round(brier(success_p, true_success), 5),
        "success_ece": round(expected_calibration_error(success_p, true_success), 5),
        "irrigation_mae_mm": round(float(np.abs(irrigation_q[..., 1] - true_irrigation).mean()), 2),
        "ndcg_at_3": round(ndcg_at_k(yield_q[..., 1], true_yield), 5),
    }
