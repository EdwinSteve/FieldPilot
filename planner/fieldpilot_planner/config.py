"""Typed views of the YAML files in configs/."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must hold a mapping")
    return data


@dataclass(frozen=True)
class YearSpan:
    first: int
    last: int

    def contains(self, year: int) -> bool:
        return self.first <= year <= self.last


@dataclass(frozen=True)
class PipelineConfig:
    max_points: int
    seed: int
    floors_m: tuple[float, float]
    first_day: date
    last_day: date
    lapse_rate_c_per_km: float
    max_gap_days: int
    max_masked_fraction: float
    soil_search_km: float
    first_sowing: date
    sowing_step_days: int
    spinup_days: int
    success_rel_yield: float
    baseline_years: YearSpan
    smoothing_days: int
    train: YearSpan
    validation: YearSpan
    test: YearSpan
    holdout_departments: tuple[str, ...]


def load_pipeline(path: Path) -> PipelineConfig:
    raw = load_yaml(path)
    points, weather, soil = raw["points"], raw["weather"], raw["soil"]
    labels, clim, splits = raw["labels"], raw["climatology"], raw["splits"]
    floors = points["floors_m"]
    return PipelineConfig(
        max_points=int(points["max_points"]),
        seed=int(points["seed"]),
        floors_m=(float(floors[0]), float(floors[1])),
        first_day=weather["first_day"],
        last_day=weather["last_day"],
        lapse_rate_c_per_km=float(weather["lapse_rate_c_per_km"]),
        max_gap_days=int(weather["max_gap_days"]),
        max_masked_fraction=float(weather["max_masked_fraction"]),
        soil_search_km=float(soil["search_radius_km"]),
        first_sowing=labels["first_sowing"],
        sowing_step_days=int(labels["sowing_step_days"]),
        spinup_days=int(labels["spinup_days"]),
        success_rel_yield=float(labels["success_rel_yield"]),
        baseline_years=YearSpan(*clim["baseline_years"]),
        smoothing_days=int(clim["smoothing_days"]),
        train=YearSpan(*splits["train"]),
        validation=YearSpan(*splits["validation"]),
        test=YearSpan(*splits["test"]),
        holdout_departments=tuple(str(d) for d in splits["holdout_departments"]),
    )
