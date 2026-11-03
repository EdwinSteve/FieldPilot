import numpy as np
import pytest

from fieldpilot_planner.clean.et0 import extraterrestrial_radiation, hargreaves, penman_monteith


def test_fao56_example_18_brussels() -> None:
    # FAO-56 Example 18: Brussels, 6 July (J = 187), 50°48'N, 100 m.
    et0 = penman_monteith(
        tmax=np.array([21.5]), tmin=np.array([12.3]), ea=np.array([1.409]),
        u2=np.array([2.078]), rs=np.array([22.07]),
        lat_deg=50.8, elevation_m=100.0, doy=np.array([187.0]),
    )  # fmt: skip
    assert et0[0] == pytest.approx(3.9, abs=0.05)


def test_fao56_example_8_extraterrestrial_radiation() -> None:
    # FAO-56 Example 8: 20°S on 3 September (J = 246): Ra = 32.2 MJ m-2 day-1.
    assert extraterrestrial_radiation(-20.0, np.array([246.0]))[0] == pytest.approx(32.2, abs=0.1)


def test_hargreaves_is_positive_and_grows_with_range() -> None:
    narrow = hargreaves(np.array([30.0]), np.array([25.0]), 3.0, np.array([180.0]))
    wide = hargreaves(np.array([34.0]), np.array([21.0]), 3.0, np.array([180.0]))
    assert 0 < narrow[0] < wide[0]
