"""NOAA CPC Oceanic Niño Index (configs/sources.yaml: oni)."""

from fieldpilot_planner.sources.http import CachedHttp

ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
SEASONS = ("DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ")


def parse_oni(text: str) -> dict[tuple[int, int], float]:
    """ONI anomaly keyed by (year, month in which the 3-month season ENDS).

    "DJF 1951" ends in February 1951; "NDJ 1950" ends in January 1951.
    """
    out: dict[tuple[int, int], float] = {}
    for line in text.splitlines()[1:]:
        parts = line.split()
        if len(parts) != 4 or parts[0] not in SEASONS:
            continue
        season, year, anomaly = parts[0], int(parts[1]), float(parts[3])
        end_month = (SEASONS.index(season) + 1) % 12 + 1
        end_year = year + 1 if season == "NDJ" else year
        out[(end_year, end_month)] = anomaly
    return out


def fetch_oni(http: CachedHttp) -> dict[tuple[int, int], float]:
    return parse_oni(http.get_text(ONI_URL))
