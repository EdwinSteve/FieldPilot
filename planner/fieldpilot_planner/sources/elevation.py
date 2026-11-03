"""Plot elevation from Open-Meteo (Copernicus DEM GLO-90)."""

from collections.abc import Sequence

from fieldpilot_planner.sources.http import CachedHttp, build_url

ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"
BATCH = 100


def fetch_elevations(http: CachedHttp, coords: Sequence[tuple[float, float]]) -> list[float]:
    elevations: list[float] = []
    for start in range(0, len(coords), BATCH):
        chunk = coords[start : start + BATCH]
        url = build_url(
            ELEVATION_URL,
            {
                "latitude": ",".join(f"{lat:.4f}" for lat, _ in chunk),
                "longitude": ",".join(f"{lon:.4f}" for _, lon in chunk),
            },
        )
        elevations.extend(float(e) for e in http.get_json(url)["elevation"])
    return elevations
