"""The cleaned dataset on disk (data/planner/clean/): one array per kind, all points aligned."""

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import numpy.typing as npt

F32 = npt.NDArray[np.float32]


@dataclass(frozen=True)
class CleanDataset:
    point_ids: npt.NDArray[np.str_]  # [P]
    departments: npt.NDArray[np.str_]  # [P]
    municipalities: npt.NDArray[np.str_]  # [P]
    day0: date
    weather: F32  # [P, D, len(WEATHER_CHANNELS)], 0 where not valid
    valid: npt.NDArray[np.bool_]  # [P, D]
    site: F32  # [P, len(SITE_FEATURES)]
    soil_profile: F32  # [P, layers, properties]
    lat: F32  # [P]
    oni_months: npt.NDArray[np.int32]  # [M] year * 12 + month - 1
    oni_values: F32  # [M]
    clim_years: npt.NDArray[np.int32]  # [Y]
    clim: F32  # [P, Y, 366, len(CLIM_OUTPUTS)]

    @property
    def days(self) -> int:
        return int(self.weather.shape[1])

    def day(self, index: int) -> date:
        return self.day0 + timedelta(days=index)

    def oni_map(self) -> dict[tuple[int, int], float]:
        return {
            (int(m) // 12, int(m) % 12 + 1): float(v)
            for m, v in zip(self.oni_months, self.oni_values, strict=True)
        }

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        np.savez(
            directory / "dataset.npz",
            point_ids=self.point_ids, departments=self.departments,
            municipalities=self.municipalities,
            day0=np.array(self.day0.toordinal()), weather=self.weather, valid=self.valid,
            site=self.site, soil_profile=self.soil_profile, lat=self.lat,
            oni_months=self.oni_months, oni_values=self.oni_values,
        )  # fmt: skip
        np.savez(directory / "climatology.npz", clim_years=self.clim_years, clim=self.clim)

    @classmethod
    def load(cls, directory: Path) -> "CleanDataset":
        with (
            np.load(directory / "dataset.npz") as data,
            np.load(directory / "climatology.npz") as clim,
        ):
            return cls(
                point_ids=data["point_ids"], departments=data["departments"],
                municipalities=data["municipalities"],
                day0=date.fromordinal(int(data["day0"])), weather=data["weather"],
                valid=data["valid"], site=data["site"], soil_profile=data["soil_profile"],
                lat=data["lat"], oni_months=data["oni_months"], oni_values=data["oni_values"],
                clim_years=clim["clim_years"], clim=clim["clim"],
            )  # fmt: skip
