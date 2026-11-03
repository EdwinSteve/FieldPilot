"""Training tensors on the GPU and the batch gather (README §8.2: no data-loader bottleneck)."""

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import torch
from torch import Tensor

from fieldpilot_planner.config import PipelineConfig, YearSpan
from fieldpilot_planner.crops import CropCard, crop_matrix
from fieldpilot_planner.dataset import CleanDataset
from fieldpilot_planner.features import (
    AHEAD_DAYS,
    HISTORY_DAYS,
    Normalization,
    Standardizer,
    context_vector,
    oni_known_at,
    prior_features,
    transform_clim,
    transform_weather,
)
from fieldpilot_planner.oracle.labels import LabelSet, sowing_years

F32 = npt.NDArray[np.float32]


@dataclass(frozen=True)
class Split:
    """Which (point, sowing) samples belong to a split."""

    years: tuple[YearSpan, ...]
    points: npt.NDArray[np.bool_]  # [P]

    def mask(
        self, years: npt.NDArray[np.int64], valid: npt.NDArray[np.bool_]
    ) -> npt.NDArray[np.bool_]:
        in_years = np.zeros_like(years, dtype=bool)
        for span in self.years:
            in_years |= (years >= span.first) & (years <= span.last)
        return np.asarray(valid & self.points[:, None] & in_years[None, :])


def standard_splits(data: CleanDataset, config: PipelineConfig, holdout: bool) -> dict[str, Split]:
    """Time splits (README §7.3); with `holdout`, the held-out departments are only tested."""
    held = np.isin(data.departments, config.holdout_departments)
    seen = ~held if holdout else np.ones_like(held)
    tested = held if holdout else seen
    return {
        "train": Split((config.train,), seen),
        "validation": Split((config.validation,), seen),
        "train+validation": Split((config.train, config.validation), seen),
        "test": Split((config.test,), tested),
    }


def sample_contexts(data: CleanDataset, sow: npt.NDArray[np.int64]) -> F32:
    """[S, len(CONTEXT_FEATURES)]: the same for every point on a sowing date."""
    oni = data.oni_map()
    out = []
    for index in sow:
        day = data.day(int(index))
        latest, trend = oni_known_at(oni, day)
        out.append(context_vector(latest, trend, day))
    return np.array(out, dtype=np.float32)


def fit_normalization(
    data: CleanDataset, labels: LabelSet, contexts: F32, train: Split, crops: list[CropCard]
) -> Normalization:
    years = sowing_years(data, labels.sow)
    train_mask = train.mask(years, labels.valid)
    last_train_day = int(labels.sow[years <= max(s.last for s in train.years)].max())
    pts = train.points
    weather = transform_weather(data.weather[pts, :last_train_day])
    weather[~data.valid[pts, :last_train_day]] = np.nan
    clim_years = data.clim_years <= max(s.last for s in train.years)
    p_idx, s_idx = np.nonzero(train_mask)
    static = np.concatenate([data.site[p_idx], contexts[s_idx]], axis=1)
    return Normalization(
        weather=Standardizer.fit(weather, axis=(0, 1)),
        clim=Standardizer.fit(transform_clim(data.clim[pts][:, clim_years]), axis=(0, 1, 2)),
        static=Standardizer.fit(static, axis=(0,)),
        crops=Standardizer.fit(crop_matrix(crops), axis=(0,)),
    )


@dataclass
class DeviceData:
    weather: Tensor  # [P, D, Cw] normalised
    clim: Tensor  # [P, Y, 366, Cc] normalised
    site: Tensor  # [P, Fsite] raw
    contexts: Tensor  # [S, Fctx] raw
    static_mean: Tensor
    static_std: Tensor
    crops: Tensor  # [C, Fc] normalised
    sow: Tensor  # [S]
    sow_year_index: Tensor  # [S] index into clim years
    sow_doy: Tensor  # [S] 0..365
    targets: Tensor  # [P, S, C, 5]: rel_yield, success, log1p irrigation, heat frac, cold frac
    prior: Tensor  # [P, S, C, 5]: B0 on the same scale (features.prior_features)

    def batch(self, p: Tensor, s: Tensor) -> tuple[Tensor, Tensor, Tensor, Tensor, Tensor]:
        """Inputs (weather, clim, static, prior) and targets of the samples (p[i], s[i])."""
        days = self.sow[s][:, None] + torch.arange(-HISTORY_DAYS, 0, device=p.device)[None, :]
        weather = self.weather[p[:, None], days].transpose(1, 2)
        doy = (self.sow_doy[s][:, None] + torch.arange(AHEAD_DAYS, device=p.device)[None, :]) % 366
        clim = self.clim[p[:, None], self.sow_year_index[s][:, None], doy].transpose(1, 2)
        static = (
            torch.cat([self.site[p], self.contexts[s]], dim=1) - self.static_mean
        ) / self.static_std
        return weather, clim, static, self.prior[p, s], self.targets[p, s]


def to_device(
    data: CleanDataset, labels: LabelSet, crops: list[CropCard], norm: Normalization,
    contexts: F32, device: torch.device,
) -> DeviceData:  # fmt: skip
    cycle = np.array([c.cycle_days for c in crops], dtype=np.float32)
    targets = prior_features(labels.labels, cycle)  # the targets share the prior's scale
    dates = [data.day(int(i)) for i in labels.sow]

    def t(array: npt.ArrayLike, dtype: torch.dtype = torch.float32) -> Tensor:
        return torch.as_tensor(np.ascontiguousarray(array), dtype=dtype, device=device)

    return DeviceData(
        weather=t(norm.weather.apply(transform_weather(data.weather))),
        clim=t(norm.clim.apply(transform_clim(data.clim))),
        site=t(data.site),
        contexts=t(contexts),
        static_mean=t(norm.static.mean),
        static_std=t(norm.static.std),
        crops=t(norm.crops.apply(crop_matrix(crops))),
        sow=t(labels.sow, torch.long),
        sow_year_index=t(np.array([d.year - int(data.clim_years[0]) for d in dates]), torch.long),
        sow_doy=t(np.array([(d - d.replace(month=1, day=1)).days for d in dates]), torch.long),
        targets=t(targets),
        prior=t(prior_features(labels.b0, cycle)),
    )
