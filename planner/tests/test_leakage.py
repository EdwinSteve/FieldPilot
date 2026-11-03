"""No input of a sample reads a day on or after its sowing date (README §7.3)."""

from datetime import date

import numpy as np
import pytest

from fieldpilot_planner.dataset import CleanDataset
from fieldpilot_planner.features import (
    CLIM_CHANNELS,
    HISTORY_DAYS,
    STATIC_FEATURES,
    WEATHER_CHANNELS,
    Normalization,
    Standardizer,
)
from fieldpilot_planner.oracle.labels import LabelSet

torch = pytest.importorskip("torch")


def _identity(width: int) -> Standardizer:
    return Standardizer(np.zeros(width, dtype=np.float32), np.ones(width, dtype=np.float32))


def test_the_weather_window_ends_the_day_before_sowing() -> None:
    from fieldpilot_planner.crops import load_crops  # noqa: PLC0415
    from fieldpilot_planner.paths import Paths  # noqa: PLC0415
    from fieldpilot_planner.training_data import to_device  # noqa: PLC0415

    days, t_channel = 1200, WEATHER_CHANNELS.index("t2m")
    weather = np.zeros((1, days, len(WEATHER_CHANNELS)), dtype=np.float32)
    weather[0, :, t_channel] = np.arange(days)  # the value is the day index
    data = CleanDataset(
        point_ids=np.array(["p0"]), departments=np.array(["41"]),
        municipalities=np.array(["41001"]),
        day0=date(2000, 1, 1), weather=weather, valid=np.ones((1, days), dtype=bool),
        site=np.zeros((1, len(STATIC_FEATURES) - 4), dtype=np.float32),
        soil_profile=np.zeros((1, 6, 7), dtype=np.float32), lat=np.zeros(1, dtype=np.float32),
        oni_months=np.array([], dtype=np.int32), oni_values=np.array([], dtype=np.float32),
        clim_years=np.array([2000, 2001, 2002], dtype=np.int32),
        clim=np.zeros((1, 3, 366, 9), dtype=np.float32),
    )  # fmt: skip
    crops = list(load_crops(Paths().configs / "crops.yaml"))
    sow = np.array([HISTORY_DAYS, 500, 700], dtype=np.int64)
    labels = LabelSet(
        sow=sow, valid=np.ones((1, 3), dtype=bool),
        labels=np.zeros((1, 3, len(crops), 5), dtype=np.float32),
        factors=np.zeros((1, 3, len(crops), 3), dtype=np.float32),
        b0=np.zeros((1, 3, len(crops), 5), dtype=np.float32),
    )  # fmt: skip
    norm = Normalization(
        _identity(len(WEATHER_CHANNELS)), _identity(len(CLIM_CHANNELS)),
        _identity(len(STATIC_FEATURES)), _identity(20),
    )  # fmt: skip
    dev = to_device(
        data, labels, crops, norm, np.zeros((3, 4), dtype=np.float32), torch.device("cpu")
    )
    window, _, _, _, _ = dev.batch(torch.tensor([0, 0, 0]), torch.tensor([0, 1, 2]))
    last_day_seen = window[:, t_channel, :].max(dim=1).values.numpy()
    np.testing.assert_array_equal(last_day_seen, sow - 1)
    np.testing.assert_array_equal(window[:, t_channel, 0].numpy(), sow - HISTORY_DAYS)
