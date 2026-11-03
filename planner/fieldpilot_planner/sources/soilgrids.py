"""ISRIC SoilGrids 2.0, read from the 1 km aggregated rasters (configs/sources.yaml: soilgrids).

The REST API takes about two minutes per point, so each layer is instead read
once, cropped to the training area, and cached. A point takes the nearest
pixel with a value in every layer: municipal centroids are often in towns,
where SoilGrids has no data.
"""

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt

COG_URL = "https://files.isric.org/soilgrids/latest/data_aggregated/1000m/{p}/{p}_{d}_mean_1000.tif"
PROPERTIES = ("sand", "clay", "soc", "phh2o", "bdod", "wv0033", "wv1500")
DEPTHS = ("0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm", "100-200cm")
LAYER_BOUNDS_CM = ((0, 5), (5, 15), (15, 30), (30, 60), (60, 100), (100, 200))
# Mapped units divided by these give conventional units (the REST API's d_factor):
# sand/clay % ; soc g/kg ; pH ; bdod kg/dm³ ; wv0033/wv1500 % volume.
D_FACTOR = {"sand": 10, "clay": 10, "soc": 10, "phh2o": 10, "bdod": 100, "wv0033": 10, "wv1500": 10}
NODATA = -32768
PIXEL_KM = 1.0


@dataclass(frozen=True)
class SoilProfile:
    lat: float  # of the pixel used
    lon: float
    layers: dict[str, tuple[float, ...]]  # property -> one value per DEPTHS entry


@dataclass(frozen=True)
class Crop:
    """One layer cropped to the training area."""

    data: npt.NDArray[np.int16]
    transform: tuple[float, float, float, float, float, float]  # GDAL affine (a, b, c, d, e, f)
    crs_wkt: str


def nearest_valid(
    valid: npt.NDArray[np.bool_], row: int, col: int, radius: int
) -> tuple[int, int] | None:
    """The valid pixel closest to (row, col) within `radius` pixels, or None."""
    r0, c0 = max(row - radius, 0), max(col - radius, 0)
    window = valid[r0 : row + radius + 1, c0 : col + radius + 1]
    rows, cols = np.nonzero(window)
    if len(rows) == 0:
        return None
    distance = (rows + r0 - row) ** 2 + (cols + c0 - col) ** 2
    best = int(np.argmin(distance))
    if distance[best] > radius**2:
        return None
    return int(rows[best] + r0), int(cols[best] + c0)


class SoilGridsRasters:
    """Requires the `data` extra (rasterio, with GDAL inside)."""

    def __init__(self, cache_dir: Path, bounds: tuple[float, float, float, float]) -> None:
        self._cache = cache_dir
        self._bounds = bounds  # lat_min, lat_max, lon_min, lon_max
        cache_dir.mkdir(parents=True, exist_ok=True)

    def layer(self, prop: str, depth: str) -> Crop:
        area = "_".join(f"{b:.2f}" for b in self._bounds)  # a different area is a different crop
        path = self._cache / f"{prop}_{depth}_{area}.npz"
        if not path.exists():
            crop = self._read(COG_URL.format(p=prop, d=depth))
            tmp = path.with_suffix(".part.npz")
            np.savez_compressed(
                tmp, data=crop.data, transform=np.array(crop.transform), crs=crop.crs_wkt
            )
            tmp.replace(path)
        with np.load(path) as f:
            return Crop(f["data"], tuple(float(v) for v in f["transform"]), str(f["crs"]))  # type: ignore[arg-type]

    def profiles(
        self, coords: Sequence[tuple[float, float]], search_km: float
    ) -> list[SoilProfile | None]:
        import rasterio.transform  # noqa: PLC0415 - optional dependency (the `data` extra)
        from rasterio.warp import transform as warp  # noqa: PLC0415

        crops = {(p, d): self.layer(p, d) for p in PROPERTIES for d in DEPTHS}
        first = crops[(PROPERTIES[0], DEPTHS[0])]
        valid = np.logical_and.reduce([c.data != NODATA for c in crops.values()])
        affine = rasterio.transform.Affine(*first.transform)
        xs, ys = warp(
            "EPSG:4326", first.crs_wkt, [lon for _, lon in coords], [lat for lat, _ in coords]
        )
        radius = math.ceil(search_km / PIXEL_KM)
        out: list[SoilProfile | None] = []
        for x, y in zip(xs, ys, strict=True):
            row, col = rasterio.transform.rowcol(affine, x, y)
            found = nearest_valid(valid, int(row), int(col), radius)
            if found is None:
                out.append(None)
                continue
            px, py = rasterio.transform.xy(affine, found[0], found[1])
            lon, lat = warp(first.crs_wkt, "EPSG:4326", [px], [py])
            layers = {
                p: tuple(float(crops[(p, d)].data[found]) / D_FACTOR[p] for d in DEPTHS)
                for p in PROPERTIES
            }
            out.append(SoilProfile(float(lat[0]), float(lon[0]), layers))
        return out

    def _read(self, url: str) -> Crop:
        import rasterio  # noqa: PLC0415
        from rasterio.warp import transform_bounds  # noqa: PLC0415
        from rasterio.windows import from_bounds  # noqa: PLC0415

        lat_min, lat_max, lon_min, lon_max = self._bounds
        env = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "GDAL_HTTP_MAX_RETRY": "5",
               "GDAL_HTTP_RETRY_DELAY": "5"}  # fmt: skip
        with rasterio.Env(**env), rasterio.open(f"/vsicurl/{url}") as ds:
            left, bottom, right, top = transform_bounds(
                "EPSG:4326", ds.crs, lon_min, lat_min, lon_max, lat_max
            )
            window = (
                from_bounds(left, bottom, right, top, ds.transform).round_offsets().round_lengths()
            )
            data = ds.read(1, window=window, boundless=True, fill_value=NODATA).astype(np.int16)
            t = ds.window_transform(window)
            return Crop(data, (t.a, t.b, t.c, t.d, t.e, t.f), ds.crs.to_wkt())


def save_profile(path: Path, profile: SoilProfile | None) -> None:
    payload = (
        None
        if profile is None
        else {"lat": profile.lat, "lon": profile.lon, "layers": profile.layers}
    )
    path.write_text(json.dumps(payload), encoding="utf-8")


def load_profile(path: Path) -> SoilProfile | None:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw is None:
        return None
    return SoilProfile(raw["lat"], raw["lon"], {k: tuple(v) for k, v in raw["layers"].items()})
