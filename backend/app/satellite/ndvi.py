"""NDVI from red and near-infrared bands, in plain Python (D058).

Pure functions over small rasters. A pixel where nir + red == 0 has no NDVI;
it stays None and is left out of every statistic, never filled.
"""

from dataclasses import dataclass

Raster = tuple[tuple[float, ...], ...]
NdviRaster = tuple[tuple[float | None, ...], ...]


@dataclass(frozen=True)
class NormalizedBox:
    """A rectangle in [0, 1] image coordinates: x to the right, y down."""

    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        if not (0 <= self.x1 < self.x2 <= 1 and 0 <= self.y1 < self.y2 <= 1):
            raise ValueError(f"not a box inside [0, 1]: {self}")

    def contains(self, x: float, y: float) -> bool:
        return self.x1 <= x < self.x2 and self.y1 <= y < self.y2


@dataclass(frozen=True)
class NdviStats:
    mean: float | None  # None when no pixel of the area has a value
    low_pct: float | None  # % of the defined pixels below the threshold
    pixels: int  # defined pixels counted


def compute_ndvi(red: Raster, nir: Raster) -> NdviRaster:
    if len(red) != len(nir) or any(len(r) != len(n) for r, n in zip(red, nir, strict=True)):
        raise ValueError("red and nir bands differ in shape")
    return tuple(
        tuple(_ndvi(r, n) for r, n in zip(red_row, nir_row, strict=True))
        for red_row, nir_row in zip(red, nir, strict=True)
    )


def zone_ndvi(ndvi: NdviRaster, area: NormalizedBox, low_threshold: float) -> NdviStats:
    """Statistics of the pixels whose centre falls inside `area`."""
    height = len(ndvi)
    values = [
        value
        for y, row in enumerate(ndvi)
        for x, value in enumerate(row)
        if value is not None and area.contains((x + 0.5) / len(row), (y + 0.5) / height)
    ]
    if not values:
        return NdviStats(None, None, 0)
    low = sum(1 for value in values if value < low_threshold)
    return NdviStats(
        round(sum(values) / len(values), 3), round(100 * low / len(values), 1), len(values)
    )


def _ndvi(red: float, nir: float) -> float | None:
    total = nir + red
    return None if total == 0 else (nir - red) / total
