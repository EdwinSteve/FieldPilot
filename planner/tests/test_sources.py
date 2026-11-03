from datetime import date

import numpy as np

from fieldpilot_planner.features import oni_known_at
from fieldpilot_planner.points import power_cell
from fieldpilot_planner.sources.datos_gov import normalize
from fieldpilot_planner.sources.oni import parse_oni
from fieldpilot_planner.sources.soilgrids import nearest_valid

ONI_TEXT = """ SEAS  YR   TOTAL   ANOM
  DJF 1951  25.01  -1.32
  NDJ 1950  26.00   0.50
  JAS 2026  29.12   2.16
"""


def test_oni_is_keyed_by_the_month_the_season_ends() -> None:
    oni = parse_oni(ONI_TEXT)
    assert oni[(1951, 2)] == -1.32  # DJF ends in February
    assert oni[(1951, 1)] == 0.50  # NDJ 1950 ends in January 1951
    assert oni[(2026, 9)] == 2.16


def test_oni_known_at_sowing_never_reads_the_future() -> None:
    oni = {(2026, m): float(m) for m in range(1, 13)}
    latest, trend = oni_known_at(oni, date(2026, 9, 15))
    assert latest == 7.0  # season ending July: two months before September
    assert trend == 3.0  # minus the season ending April


def test_names_and_cells() -> None:
    assert normalize("Maíz") == normalize("MAIZ") == "MAIZ"
    assert power_cell(2.93, -75.28) == power_cell(2.99, -75.01)
    assert power_cell(2.93, -75.28) != power_cell(3.01, -75.28)


def test_nearest_valid_pixel() -> None:
    valid = np.zeros((7, 7), dtype=bool)
    valid[1, 5] = valid[4, 3] = True
    assert nearest_valid(valid, 3, 3, radius=3) == (4, 3)
    assert nearest_valid(valid, 3, 3, radius=0) is None
