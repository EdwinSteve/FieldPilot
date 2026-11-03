"""Crop cards: the published requirements of each candidate crop (configs/crops.yaml).

A crop enters the model as its card, not as an id (README §7.1), so the card
also defines the crop's feature vector.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from fieldpilot_planner.config import load_yaml

MAX_CYCLE_DAYS = 210  # the climatology window ahead (README §7.1)


def midpoint(value: float | Sequence[float]) -> float:
    """A published range is used at its midpoint: the one project convention in the cards."""
    if isinstance(value, int | float):
        return float(value)
    low, high = value
    return (float(low) + float(high)) / 2


@dataclass(frozen=True)
class CropCard:
    crop: str
    name_es: str
    eva_names: tuple[str, ...]
    kill_c: float
    tmin_c: float
    topt_min_c: float
    topt_max_c: float
    tmax_c: float
    ph_min: float
    ph_opt_min: float
    ph_opt_max: float
    ph_max: float
    stage_days: tuple[int, int, int, int]  # initial, development, mid, late (FAO-56 Table 11)
    kc_ini: float
    kc_mid: float
    kc_end: float
    root_depth_m: float
    depletion_p: float
    ky: float

    @property
    def cycle_days(self) -> int:
        return sum(self.stage_days)

    def kc_curve(self) -> npt.NDArray[np.float32]:
        """Daily Kc over the cycle: FAO-56 single crop coefficient curve (Fig. 25)."""
        ini, dev, mid, late = self.stage_days
        return np.concatenate(
            [
                np.full(ini, self.kc_ini),
                np.linspace(self.kc_ini, self.kc_mid, dev + 1)[1:],
                np.full(mid, self.kc_mid),
                np.linspace(self.kc_mid, self.kc_end, late + 1)[1:],
            ]
        ).astype(np.float32)

    def feature_vector(self) -> list[float]:
        ini, dev, mid, late = self.stage_days
        return [
            self.kill_c, self.tmin_c, self.topt_min_c, self.topt_max_c, self.tmax_c,
            self.ph_min, self.ph_opt_min, self.ph_opt_max, self.ph_max,
            float(ini), float(dev), float(mid), float(late), float(self.cycle_days),
            self.kc_ini, self.kc_mid, self.kc_end,
            self.root_depth_m, self.depletion_p, self.ky,
        ]  # fmt: skip


CROP_FEATURES = (
    "kill_c", "tmin_c", "topt_min_c", "topt_max_c", "tmax_c",
    "ph_min", "ph_opt_min", "ph_opt_max", "ph_max",
    "days_initial", "days_development", "days_mid", "days_late", "cycle_days",
    "kc_ini", "kc_mid", "kc_end", "root_depth_m", "depletion_p", "ky",
)  # fmt: skip


def _card(raw: dict[str, Any]) -> CropCard:
    eco, stages, kc = raw["ecocrop"], raw["stages_days"], raw["kc"]
    card = CropCard(
        crop=str(raw["crop"]),
        name_es=str(raw["display_name"]["es"]),
        eva_names=tuple(str(n) for n in raw["eva_names"]),
        kill_c=float(eco["kill_c"]),
        tmin_c=float(eco["tmin_c"]),
        topt_min_c=float(eco["topt_min_c"]),
        topt_max_c=float(eco["topt_max_c"]),
        tmax_c=float(eco["tmax_c"]),
        ph_min=float(eco["ph_min"]),
        ph_opt_min=float(eco["ph_opt_min"]),
        ph_opt_max=float(eco["ph_opt_max"]),
        ph_max=float(eco["ph_max"]),
        stage_days=(
            int(stages["initial"]),
            int(stages["development"]),
            int(stages["mid"]),
            int(stages["late"]),
        ),
        kc_ini=midpoint(kc["ini"]),
        kc_mid=midpoint(kc["mid"]),
        kc_end=midpoint(kc["end"]),
        root_depth_m=midpoint(raw["root_depth_m"]),
        depletion_p=float(raw["depletion_p"]),
        ky=float(raw["ky"]),
    )
    _validate(card)
    return card


def _validate(card: CropCard) -> None:
    temps = (card.tmin_c, card.topt_min_c, card.topt_max_c, card.tmax_c)
    phs = (card.ph_min, card.ph_opt_min, card.ph_opt_max, card.ph_max)
    problems = []
    if list(temps) != sorted(temps):
        problems.append("temperatures not ordered")
    if list(phs) != sorted(phs):
        problems.append("pH not ordered")
    if not 0 < card.cycle_days <= MAX_CYCLE_DAYS:
        problems.append(f"cycle of {card.cycle_days} days outside 1..{MAX_CYCLE_DAYS}")
    if not 0 < card.depletion_p < 1 or card.root_depth_m <= 0 or card.ky <= 0:
        problems.append("p, root depth or Ky out of range")
    if problems:
        raise ValueError(f"crop {card.crop}: {'; '.join(problems)}")


def load_crops(path: Path) -> tuple[CropCard, ...]:
    cards = tuple(_card(raw) for raw in load_yaml(path)["crops"])
    names = [c.crop for c in cards]
    if len(set(names)) != len(names):
        raise ValueError("duplicate crop in crops.yaml")
    return cards


def crop_matrix(cards: Sequence[CropCard]) -> npt.NDArray[np.float32]:
    return np.array([c.feature_vector() for c in cards], dtype=np.float32)
