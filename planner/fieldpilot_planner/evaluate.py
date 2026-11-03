"""Stage `evaluate`: the network against B0 and B1 on the test split (README §7.3)."""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from fieldpilot_planner.crops import CropCard
from fieldpilot_planner.dataset import CleanDataset
from fieldpilot_planner.metrics import spearman, summary
from fieldpilot_planner.oracle.labels import LabelSet, sowing_years
from fieldpilot_planner.sources.datos_gov import EvaRecord, normalize
from fieldpilot_planner.train import Samples

F32 = npt.NDArray[np.float32]
WEEKS = 53


@dataclass(frozen=True)
class Predictions:
    """[N, C, 3] quantiles, [N, C] probability, [N, C, 3] irrigation in mm."""

    rel_yield: F32
    success: F32
    irrigation_mm: F32


def from_network(raw: F32) -> Predictions:
    return Predictions(
        rel_yield=np.clip(raw[..., 0:3], 0.0, 1.0),
        success=(1 / (1 + np.exp(-raw[..., 3]))).astype(np.float32),
        irrigation_mm=np.maximum(np.expm1(raw[..., 4:7]), 0.0),
    )


def from_b0(labels: LabelSet, samples: Samples) -> Predictions:
    """B0 is a point estimate: all three quantiles equal, probability 0 or 1."""
    b0 = labels.b0[samples.p, samples.s]
    return Predictions(
        rel_yield=np.repeat(b0[..., 0:1], 3, axis=-1),
        success=b0[..., 1],
        irrigation_mm=np.repeat(b0[..., 2:3], 3, axis=-1),
    )


def _week(data: CleanDataset, sow: npt.NDArray[np.int64]) -> npt.NDArray[np.int64]:
    return np.array([(data.day(int(i)).timetuple().tm_yday - 1) // 7 for i in sow], dtype=np.int64)


def from_b1(data: CleanDataset, labels: LabelSet, train: Samples, samples: Samples) -> Predictions:
    """B1: each point's training-year history for the same week of the year."""
    weeks = _week(data, labels.sow)
    n_points, n_crops = labels.labels.shape[0], labels.labels.shape[2]
    table = np.full((n_points, WEEKS, n_crops, 5), np.nan, dtype=np.float32)
    groups: dict[tuple[int, int], list[int]] = defaultdict(list)
    for p, s in zip(train.p, train.s, strict=True):
        groups[(int(p), int(weeks[s]))].append(int(s))
    for (p, w), s_list in groups.items():
        history = labels.labels[p, s_list]  # [n, C, 5]
        table[p, w, :, 0:3] = np.percentile(history[..., 0], [10, 50, 90], axis=0).T
        table[p, w, :, 3] = history[..., 1].mean(axis=0)
        table[p, w, :, 4] = np.median(history[..., 2], axis=0)
    rows = table[samples.p, weeks[samples.s]]
    rows = np.where(np.isnan(rows), np.nanmean(table, axis=(0, 1))[None], rows)
    return Predictions(rows[..., 0:3], rows[..., 3], np.repeat(rows[..., 4:5], 3, axis=-1))


def score(pred: Predictions, labels: LabelSet, samples: Samples) -> dict[str, float]:
    truth = labels.labels[samples.p, samples.s]
    return summary(
        pred.rel_yield,
        pred.success,
        pred.irrigation_mm,
        truth[..., 0],
        truth[..., 1],
        truth[..., 2],
    )


def eva_spearman(
    data: CleanDataset, labels: LabelSet, crops: Sequence[CropCard], samples: Samples,
    pred: Predictions, eva: Sequence[EvaRecord],
) -> dict[str, float | None]:  # fmt: skip
    """Per crop: predicted annual mean relative yield vs EVA yield, as anomalies per municipality.

    This is the only check against reality (README §7.3); None means too few pairs.
    """
    years = sowing_years(data, labels.sow)[samples.s]
    observed: dict[tuple[str, str, int], float] = {
        (r.municipality, r.crop_name, r.year): r.production_t / r.harvested_ha
        for r in eva
        if r.harvested_ha > 0
    }
    out: dict[str, float | None] = {}
    for c, crop in enumerate(crops):
        names = {normalize(n) for n in crop.eva_names}
        pairs: dict[tuple[str, int], list[float]] = defaultdict(list)
        for i, p in enumerate(samples.p):
            pairs[(str(data.municipalities[p]), int(years[i]))].append(
                float(pred.rel_yield[i, c, 1])
            )
        predicted, actual, municipality = [], [], []
        for (mun, year), values in pairs.items():
            found = [observed[(mun, n, year)] for n in names if (mun, n, year) in observed]
            if found:
                predicted.append(float(np.mean(values)))
                actual.append(found[0])
                municipality.append(mun)
        rho = _anomaly_spearman(predicted, actual, municipality)
        out[crop.crop] = None if np.isnan(rho) else round(rho, 3)
    return out


def _anomaly_spearman(
    predicted: list[float], actual: list[float], municipality: list[str]
) -> float:
    pred, act, mun = np.array(predicted), np.array(actual), np.array(municipality)
    for m in set(municipality):
        members = mun == m
        pred[members] -= pred[members].mean()
        act[members] -= act[members].mean()
    keep = np.array([np.sum(mun == m) >= 2 for m in mun]) if len(mun) else np.array([], dtype=bool)
    return spearman(pred[keep], act[keep]) if keep.any() else float("nan")


def adopted(network: dict[str, float], b0: dict[str, float]) -> bool:
    """README §7.3: the network is used only if it beats B0 on pinball and NDCG@3."""
    return (
        network["rel_yield_pinball"] < b0["rel_yield_pinball"]
        and network["ndcg_at_3"] > b0["ndcg_at_3"]
    )
