"""Where the pipeline reads configuration and writes data, runs and bundles."""

import os
from dataclasses import dataclass, field
from pathlib import Path

PLANNER_DIR = Path(__file__).resolve().parent.parent
DATA_ENV = "FIELDPILOT_PLANNER_DATA"  # optional: keep the data on another disk


def _default_data() -> Path:
    override = os.environ.get(DATA_ENV)
    return Path(override) if override else PLANNER_DIR.parent / "data" / "planner"


@dataclass(frozen=True)
class Paths:
    """All locations derive from the planner folder, so the pipeline runs from any cwd."""

    planner: Path = PLANNER_DIR
    data: Path = field(default_factory=_default_data)

    @property
    def configs(self) -> Path:
        return self.planner / "configs"

    @property
    def raw(self) -> Path:
        return self.data / "raw"

    @property
    def clean(self) -> Path:
        return self.data / "clean"

    @property
    def labels(self) -> Path:
        return self.data / "labels"

    @property
    def runs(self) -> Path:
        return self.data / "runs"

    @property
    def models(self) -> Path:
        return self.planner / "models"

    @property
    def points_csv(self) -> Path:
        return self.configs / "points.csv"
