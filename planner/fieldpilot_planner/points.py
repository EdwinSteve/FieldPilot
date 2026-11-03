"""Training points: farming municipalities, one per POWER grid cell (README §4.2)."""

import csv
import math
import random
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from fieldpilot_planner.config import PipelineConfig
from fieldpilot_planner.crops import CropCard
from fieldpilot_planner.sources.datos_gov import (
    EvaRecord,
    Municipality,
    fetch_eva,
    fetch_municipalities,
    normalize,
)
from fieldpilot_planner.sources.elevation import fetch_elevations
from fieldpilot_planner.sources.http import CachedHttp

POWER_CELL_DEG = (0.5, 0.625)  # MERRA-2 grid behind POWER's meteorology


@dataclass(frozen=True)
class Point:
    id: str
    municipality: str
    department: str
    name: str
    lat: float
    lon: float
    elevation_m: float
    crop_area_ha: float


def power_cell(lat: float, lon: float) -> tuple[int, int]:
    return (math.floor((lat + 90) / POWER_CELL_DEG[0]), math.floor((lon + 180) / POWER_CELL_DEG[1]))


def crop_area_by_municipality(
    records: Sequence[EvaRecord], crops: Sequence[CropCard]
) -> dict[str, float]:
    names = {normalize(n) for c in crops for n in c.eva_names}
    area: dict[str, float] = defaultdict(float)
    for r in records:
        if r.crop_name in names:
            area[r.municipality] += r.sown_ha
    return {m: a for m, a in area.items() if a > 0}


def one_per_cell(
    municipalities: Sequence[Municipality], area: dict[str, float]
) -> list[Municipality]:
    """Points in one cell share its weather; the municipality with most crop area is kept."""
    best: dict[tuple[int, int], Municipality] = {}
    for m in municipalities:
        if m.code not in area:
            continue
        cell = power_cell(m.lat, m.lon)
        if cell not in best or area[m.code] > area[best[cell].code]:
            best[cell] = m
    return sorted(best.values(), key=lambda m: m.code)


def floor_of(elevation_m: float, floors_m: tuple[float, float]) -> int:
    return sum(elevation_m >= f for f in floors_m)


def stratified_cap(points: list[Point], config: PipelineConfig) -> list[Point]:
    """Above the cap, sample each thermal floor in proportion to its size, with a fixed seed."""
    if len(points) <= config.max_points:
        return points
    rng = random.Random(config.seed)
    by_floor: dict[int, list[Point]] = defaultdict(list)
    for p in points:
        by_floor[floor_of(p.elevation_m, config.floors_m)].append(p)
    kept: list[Point] = []
    for group in by_floor.values():
        share = round(config.max_points * len(group) / len(points))
        kept.extend(rng.sample(group, min(share, len(group))))
    return sorted(kept, key=lambda p: p.municipality)


def select_points(
    http: CachedHttp, crops: Sequence[CropCard], config: PipelineConfig
) -> list[Point]:
    municipalities = fetch_municipalities(http)
    area = crop_area_by_municipality(
        fetch_eva(http, [n for c in crops for n in c.eva_names]), crops
    )
    chosen = one_per_cell(municipalities, area)
    elevations = fetch_elevations(http, [(m.lat, m.lon) for m in chosen])
    points = [
        Point("", m.code, m.department, m.name, m.lat, m.lon, elev, round(area[m.code], 1))
        for m, elev in zip(chosen, elevations, strict=True)
    ]
    capped = stratified_cap(points, config)
    return [Point(**{**asdict(p), "id": f"p{i:03d}"}) for i, p in enumerate(capped)]


def write_points(path: Path, points: Sequence[Point]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[f.name for f in fields(Point)])
        writer.writeheader()
        writer.writerows(asdict(p) for p in points)


def read_points(path: Path) -> list[Point]:
    with path.open(encoding="utf-8") as handle:
        return [
            Point(
                id=row["id"],
                municipality=row["municipality"],
                department=row["department"],
                name=row["name"],
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                elevation_m=float(row["elevation_m"]),
                crop_area_ha=float(row["crop_area_ha"]),
            )
            for row in csv.DictReader(handle)
        ]
