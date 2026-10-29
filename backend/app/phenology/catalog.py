"""Crop catalog: immutable specs loaded and validated from `config/crops/*.yaml`.

Every numeric field must name a source declared in the same file, so no
value can enter the system without saying where it comes from (D017).
Any inconsistency stops the application at startup.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from itertools import pairwise
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from app.domain.enums import ActionType, AutonomyLevel

Verification = Literal["verified", "partially_verified", "project_convention", "demo_value"]

MAX_CROP_COEFFICIENT = 2.0


class CatalogError(ValueError):
    """The crop catalog is missing, malformed or inconsistent."""


# --- domain specs ---------------------------------------------------------


@dataclass(frozen=True)
class Source:
    key: str
    citation: str
    verification: Verification
    url: str | None = None
    verified_on: date | None = None
    note: str | None = None


@dataclass(frozen=True)
class MoistureTarget:
    """Desired soil moisture, in percent of field capacity (D015)."""

    low_pct_fc: float  # irrigation is considered below this
    high_pct_fc: float  # irrigation aims for this


@dataclass(frozen=True)
class StageSpec:
    name: str
    display_name: Mapping[str, str]
    gdd_start: float
    moisture_target: MoistureTarget
    nutrient_need_kg_ha: Mapping[str, float]
    autonomy: Mapping[ActionType, AutonomyLevel]
    sources: Mapping[str, str]  # field name -> source key

    def level_for(self, action_type: ActionType) -> AutonomyLevel | None:
        """Stage-specific level, if any. The gate keeps the stricter one (D006)."""
        return self.autonomy.get(action_type)


@dataclass(frozen=True)
class KcPoint:
    """One point of the FAO-56 Kc curve, mapped to degree-days (D030)."""

    name: str
    gdd: float
    kc: float
    sources: Mapping[str, str]  # field name -> source key
    note: str | None = None


@dataclass(frozen=True)
class CropSpec:
    name: str
    display_name: Mapping[str, str]
    base_temp_c: float
    upper_temp_c: float
    maturity_gdd: float
    stages: tuple[StageSpec, ...]  # ordered by gdd_start; the first starts at 0
    kc_curve: tuple[KcPoint, ...]  # from 0 to maturity_gdd, independent of the stages
    sources: Mapping[str, Source]
    field_sources: Mapping[str, str]  # crop-level field -> source key
    reviewed_by_agronomist: bool
    calibration_note: str

    def stage(self, name: str) -> StageSpec:
        for stage in self.stages:
            if stage.name == name:
                return stage
        raise KeyError(f"{self.name} has no stage {name!r}")

    def kc_point(self, name: str) -> KcPoint:
        for point in self.kc_curve:
            if point.name == name:
                return point
        raise KeyError(f"{self.name} has no Kc point {name!r}")


CropCatalog = Mapping[str, CropSpec]


# --- YAML schema (parsing only) ------------------------------------------


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _SourceModel(_Strict):
    citation: str
    verification: Verification
    url: str | None = None
    verified_on: date | None = None
    note: str | None = None


class _Value(_Strict):
    value: float
    source: str


class _KcPoint(_Strict):
    name: str
    gdd: _Value
    kc: _Value
    note: str | None = None


class _Moisture(_Strict):
    low: float
    high: float
    source: str


class _Nutrients(_Strict):
    values: dict[str, float]
    source: str


class _Stage(_Strict):
    name: str
    display_name: dict[str, str]
    gdd_start: _Value
    moisture_target_pct_fc: _Moisture
    nutrient_need_kg_ha: _Nutrients
    autonomy: dict[ActionType, AutonomyLevel]


class _Gdd(_Strict):
    base_temp_c: _Value
    upper_temp_c: _Value
    maturity_gdd: _Value


class _Crop(_Strict):
    crop: str
    display_name: dict[str, str]
    reviewed_by_agronomist: bool
    calibration_note: str
    sources: dict[str, _SourceModel]
    gdd: _Gdd
    stages: list[_Stage]
    kc_curve: list[_KcPoint]


# --- loading --------------------------------------------------------------


def load_crop_catalog(directory: Path, max_moisture_pct_fc: float) -> CropCatalog:
    """Load every `*.yaml` crop in `directory`.

    `max_moisture_pct_fc` is the safety limit for irrigation; no stage may
    target moisture above it.
    """
    files = sorted(directory.glob("*.yaml"))
    if not files:
        raise CatalogError(f"no crop files in {directory}")
    catalog: dict[str, CropSpec] = {}
    for path in files:
        crop = load_crop_file(path, max_moisture_pct_fc)
        if crop.name in catalog:
            raise CatalogError(f"crop {crop.name!r} defined twice")
        catalog[crop.name] = crop
    return catalog


def load_crop_file(path: Path, max_moisture_pct_fc: float) -> CropSpec:
    """Parse and validate one crop file."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        model = _Crop.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise CatalogError(f"{path.name}: {error}") from error
    crop = _to_spec(model)
    _validate(crop, max_moisture_pct_fc, where=path.name)
    return crop


def _to_spec(model: _Crop) -> CropSpec:
    sources = {key: Source(key=key, **source.model_dump()) for key, source in model.sources.items()}
    stages = tuple(_stage_spec(stage) for stage in model.stages)
    return CropSpec(
        name=model.crop,
        display_name=model.display_name,
        base_temp_c=model.gdd.base_temp_c.value,
        upper_temp_c=model.gdd.upper_temp_c.value,
        maturity_gdd=model.gdd.maturity_gdd.value,
        stages=stages,
        kc_curve=tuple(_kc_point(point) for point in model.kc_curve),
        sources=sources,
        field_sources={
            "base_temp_c": model.gdd.base_temp_c.source,
            "upper_temp_c": model.gdd.upper_temp_c.source,
            "maturity_gdd": model.gdd.maturity_gdd.source,
        },
        reviewed_by_agronomist=model.reviewed_by_agronomist,
        calibration_note=model.calibration_note,
    )


def _stage_spec(stage: _Stage) -> StageSpec:
    return StageSpec(
        name=stage.name,
        display_name=stage.display_name,
        gdd_start=stage.gdd_start.value,
        moisture_target=MoistureTarget(
            stage.moisture_target_pct_fc.low, stage.moisture_target_pct_fc.high
        ),
        nutrient_need_kg_ha=stage.nutrient_need_kg_ha.values,
        autonomy=stage.autonomy,
        sources={
            "gdd_start": stage.gdd_start.source,
            "moisture_target_pct_fc": stage.moisture_target_pct_fc.source,
            "nutrient_need_kg_ha": stage.nutrient_need_kg_ha.source,
        },
    )


def _kc_point(point: _KcPoint) -> KcPoint:
    return KcPoint(
        name=point.name,
        gdd=point.gdd.value,
        kc=point.kc.value,
        sources={"gdd": point.gdd.source, "kc": point.kc.source},
        note=point.note,
    )


def _validate(crop: CropSpec, max_moisture_pct_fc: float, where: str) -> None:
    problems = [
        *_source_problems(crop),
        *_temperature_problems(crop),
        *_stage_order_problems(crop),
        *_kc_curve_problems(crop),
        *(p for stage in crop.stages for p in _stage_problems(stage, max_moisture_pct_fc)),
    ]
    if problems:
        raise CatalogError(f"{where}: " + "; ".join(problems))


def _source_problems(crop: CropSpec) -> list[str]:
    referenced = [*crop.field_sources.values()]
    referenced += [key for stage in crop.stages for key in stage.sources.values()]
    referenced += [key for point in crop.kc_curve for key in point.sources.values()]
    return [f"unknown source {key!r}" for key in sorted(set(referenced) - set(crop.sources))]


def _temperature_problems(crop: CropSpec) -> list[str]:
    if crop.base_temp_c >= crop.upper_temp_c:
        return ["base temperature must be below the upper temperature"]
    return []


def _stage_order_problems(crop: CropSpec) -> list[str]:
    if not crop.stages:
        return ["at least one stage is required"]
    problems: list[str] = []
    if crop.stages[0].gdd_start != 0:
        problems.append("the first stage must start at 0 GDD")
    starts = [stage.gdd_start for stage in crop.stages]
    if any(later <= earlier for earlier, later in pairwise(starts)):
        problems.append("stage gdd_start values must strictly increase")
    names = [stage.name for stage in crop.stages]
    if len(set(names)) != len(names):
        problems.append("stage names must be unique")
    if crop.maturity_gdd <= starts[-1]:
        problems.append("maturity_gdd must be after the last stage starts")
    return problems


def _kc_curve_problems(crop: CropSpec) -> list[str]:
    curve = crop.kc_curve
    if len(curve) < 2:
        return ["the Kc curve needs at least two points"]
    problems: list[str] = []
    if curve[0].gdd != 0:
        problems.append("the Kc curve must start at 0 GDD")
    if any(later.gdd <= earlier.gdd for earlier, later in pairwise(curve)):
        problems.append("Kc curve gdd values must strictly increase")
    if curve[-1].gdd != crop.maturity_gdd:
        problems.append("the Kc curve must end at maturity_gdd")
    names = [point.name for point in curve]
    if len(set(names)) != len(names):
        problems.append("Kc point names must be unique")
    problems += [
        f"Kc point {point.name}: crop coefficient {point.kc} outside [0, 2]"
        for point in curve
        if not 0 <= point.kc <= MAX_CROP_COEFFICIENT
    ]
    return problems


def _stage_problems(stage: StageSpec, max_moisture_pct_fc: float) -> list[str]:
    problems: list[str] = []
    target = stage.moisture_target
    if not 0 < target.low_pct_fc < target.high_pct_fc:
        problems.append(f"{stage.name}: moisture target needs 0 < low < high")
    if target.high_pct_fc > max_moisture_pct_fc:
        problems.append(
            f"{stage.name}: moisture target {target.high_pct_fc} % exceeds the safety "
            f"limit {max_moisture_pct_fc} %"
        )
    if any(amount < 0 for amount in stage.nutrient_need_kg_ha.values()):
        problems.append(f"{stage.name}: nutrient needs cannot be negative")
    return problems
