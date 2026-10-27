"""The maize catalog is cited in the defense: every value must say where it comes from."""

import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.domain.enums import ActionType, AutonomyLevel, strictest
from app.phenology.catalog import CatalogError, CropSpec, load_crop_catalog, load_crop_file
from tests.conftest import CROPS_DIR, SAFETY_MAX_MOISTURE_PCT_FC

MAIZE_FILE = CROPS_DIR / "maize.yaml"
SOURCED_STAGE_FIELDS = (
    "gdd_start",
    "crop_coefficient",
    "moisture_target_pct_fc",
    "nutrient_need_kg_ha",
)

# Cumulative GDD in °F·day from the cited table (AGF-0101 / PMR 1009).
PUBLISHED_GDD_F = {
    "vegetative": 100,  # VE
    "flowering": 1420,  # VT / R1
    "grain_fill": 1686,  # R2
    "maturity_harvest": 2324,  # R5
}
PUBLISHED_MATURITY_GDD_F = 2650  # R6


def raw_maize() -> dict[str, Any]:
    raw: dict[str, Any] = yaml.safe_load(MAIZE_FILE.read_text(encoding="utf-8"))
    return raw


# --- provenance -----------------------------------------------------------


def test_every_value_in_the_raw_file_names_a_declared_source() -> None:
    raw = raw_maize()
    declared = set(raw["sources"])

    for field in ("base_temp_c", "upper_temp_c", "maturity_gdd"):
        assert raw["gdd"][field]["source"] in declared, field
    for stage in raw["stages"]:
        for field in SOURCED_STAGE_FIELDS:
            assert stage[field]["source"] in declared, f"{stage['name']}.{field}"


def test_verified_sources_carry_a_url_and_a_date(maize: CropSpec) -> None:
    for source in maize.sources.values():
        if source.verification in ("verified", "partially_verified"):
            assert source.url, source.key
            assert source.verified_on is not None, source.key


def test_catalog_is_not_presented_as_agronomist_reviewed(maize: CropSpec) -> None:
    assert maize.reviewed_by_agronomist is False
    assert "calibrated" in maize.calibration_note


def test_demo_values_are_never_labelled_as_verified(maize: CropSpec) -> None:
    for stage in maize.stages:
        for field in ("moisture_target_pct_fc", "nutrient_need_kg_ha"):
            assert maize.sources[stage.sources[field]].verification == "demo_value"


@pytest.mark.parametrize(("stage", "gdd_f"), PUBLISHED_GDD_F.items())
def test_stage_thresholds_match_the_published_table(
    maize: CropSpec, stage: str, gdd_f: float
) -> None:
    assert maize.stage(stage).gdd_start == pytest.approx(gdd_f / 1.8, abs=0.05)
    assert maize.stage(stage).sources["gdd_start"] == "pmr1009"


def test_maturity_matches_black_layer(maize: CropSpec) -> None:
    assert maize.maturity_gdd == pytest.approx(PUBLISHED_MATURITY_GDD_F / 1.8, abs=0.05)


def test_kc_values_match_fao56(maize: CropSpec) -> None:
    assert maize.stage("flowering").kc_start == 1.20
    assert maize.stage("maturity_harvest").kc_end == 0.60
    assert maize.stage("sowing").kc_start == 0.30


# --- agronomic intent (demo) ----------------------------------------------


def test_flowering_has_the_highest_moisture_floor(maize: CropSpec) -> None:
    flowering = maize.stage("flowering").moisture_target.low_pct_fc
    others = [s.moisture_target.low_pct_fc for s in maize.stages if s.name != "flowering"]

    assert all(flowering > other for other in others)


def test_flowering_moisture_target_is_70_to_80(maize: CropSpec) -> None:
    target = maize.stage("flowering").moisture_target

    assert (target.low_pct_fc, target.high_pct_fc) == (70.0, 80.0)


def test_sowing_does_not_tighten_irrigation(maize: CropSpec) -> None:
    assert maize.stage("sowing").level_for(ActionType.IRRIGATION) is None


def test_irrigation_at_sowing_stays_autonomous(maize: CropSpec) -> None:
    # The gate (step 5) applies strictest(default, stage level) per D006.
    default = AutonomyLevel.AUTONOMOUS  # irrigation default in autonomy.yaml (step 5)
    stage_level = maize.stage("sowing").level_for(ActionType.IRRIGATION)
    levels = [default] if stage_level is None else [default, stage_level]

    assert strictest(*levels) is AutonomyLevel.AUTONOMOUS


def test_maturity_tightens_irrigation_to_notify(maize: CropSpec) -> None:
    stage = maize.stage("maturity_harvest")

    assert stage.level_for(ActionType.IRRIGATION) is AutonomyLevel.NOTIFY


def test_no_stage_targets_moisture_above_the_safety_limit(maize: CropSpec) -> None:
    assert all(s.moisture_target.high_pct_fc <= SAFETY_MAX_MOISTURE_PCT_FC for s in maize.stages)


# --- validation: one broken file per rule ---------------------------------

Mutation = Callable[[dict[str, Any]], None]


def _stage(raw: dict[str, Any], name: str) -> dict[str, Any]:
    return next(s for s in raw["stages"] if s["name"] == name)


def _set(path: list[str | int], value: Any) -> Mutation:
    def mutate(raw: dict[str, Any]) -> None:
        target: Any = raw
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return mutate


INVALID: dict[str, tuple[Mutation, str]] = {
    "unknown source": (_set(["stages", 0, "gdd_start", "source"], "wikipedia"), "unknown source"),
    "missing source": (
        lambda raw: raw["stages"][0]["gdd_start"].pop("source"),
        "source",
    ),
    "first stage not at 0": (_set(["stages", 0, "gdd_start", "value"], 5.0), "start at 0"),
    "non-increasing stages": (_set(["stages", 2, "gdd_start", "value"], 10.0), "increase"),
    "duplicate stage name": (_set(["stages", 1, "name"], "sowing"), "unique"),
    "kc above 2": (_set(["stages", 3, "crop_coefficient", "end"], 2.5), "outside"),
    "moisture above safety limit": (
        _set(["stages", 3, "moisture_target_pct_fc", "high"], 90.0),
        "safety limit",
    ),
    "moisture low not below high": (
        _set(["stages", 3, "moisture_target_pct_fc", "low"], 80.0),
        "low < high",
    ),
    "base not below upper": (_set(["gdd", "base_temp_c", "value"], 30.0), "base temperature"),
    "maturity before last stage": (_set(["gdd", "maturity_gdd", "value"], 1000.0), "maturity"),
    "unknown field": (_set(["stages", 0, "water_need_mm_per_day"], 5.0), "Extra inputs"),
    "unknown action type": (
        _set(["stages", 0, "autonomy"], {"teleport": "approval"}),
        "teleport",
    ),
    "kc jump between stages": (
        _set(["stages", 3, "crop_coefficient", "start"], 1.0),
        "jumps",
    ),
    "negative nutrient": (
        _set(["stages", 0, "nutrient_need_kg_ha", "values", "N"], -1.0),
        "negative",
    ),
}


@pytest.mark.parametrize("case", INVALID)
def test_invalid_catalog_fails_fast(case: str, tmp_path: Path) -> None:
    mutate, message = INVALID[case]
    raw = copy.deepcopy(raw_maize())
    mutate(raw)
    path = tmp_path / "maize.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")

    with pytest.raises(CatalogError, match=message):
        load_crop_file(path, SAFETY_MAX_MOISTURE_PCT_FC)


def test_empty_catalog_directory_fails(tmp_path: Path) -> None:
    with pytest.raises(CatalogError, match="no crop files"):
        load_crop_catalog(tmp_path, SAFETY_MAX_MOISTURE_PCT_FC)


def test_stricter_safety_limit_rejects_the_shipped_catalog() -> None:
    with pytest.raises(CatalogError, match="safety limit"):
        load_crop_catalog(CROPS_DIR, max_moisture_pct_fc=75.0)
