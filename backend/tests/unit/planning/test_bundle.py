"""The planner bundle: checked against its manifest, then the right recommender (D081)."""

import json
import shutil
from pathlib import Path

import pytest
from fieldpilot_planner.manifest import file_digest

from app.domain.errors import ConfigError
from app.planning.bundle import load_bundle, newest_bundle
from app.planning.climatology import B0_MODEL_ID
from app.planning.setup import build_recommender
from app.settings import REPO_ROOT

PLANNER = REPO_ROOT / "planner"
BUNDLE = newest_bundle(PLANNER / "models")


@pytest.fixture
def bundle_copy(tmp_path: Path) -> Path:
    assert BUNDLE is not None
    target = tmp_path / BUNDLE.name
    shutil.copytree(BUNDLE, target)
    return target


def test_the_committed_bundle_loads_and_is_adopted() -> None:
    assert BUNDLE is not None
    bundle = load_bundle(BUNDLE)
    assert bundle.adopted
    assert "maize" in [c.crop for c in bundle.crops]


def test_a_tampered_bundle_stops_the_app(bundle_copy: Path) -> None:
    metrics = bundle_copy / "metrics.json"
    metrics.write_text(metrics.read_text(encoding="utf-8").replace("true", "false", 1))
    with pytest.raises(ConfigError, match=r"metrics\.json"):
        load_bundle(bundle_copy)


def test_the_adopted_network_serves_the_plan() -> None:
    assert BUNDLE is not None
    assert build_recommender(PLANNER, None).model_id == BUNDLE.name


def test_a_bundle_that_did_not_beat_b0_serves_b0(bundle_copy: Path) -> None:
    metrics = json.loads((bundle_copy / "metrics.json").read_text(encoding="utf-8"))
    metrics["adopted"] = False
    _rewrite(bundle_copy, "metrics.json", json.dumps(metrics, indent=1))
    assert build_recommender(PLANNER, bundle_copy).model_id == B0_MODEL_ID


def test_without_any_bundle_b0_serves_the_plan(tmp_path: Path) -> None:
    planner = tmp_path / "planner"
    shutil.copytree(PLANNER / "configs", planner / "configs")
    assert build_recommender(planner, None).model_id == B0_MODEL_ID


def _rewrite(bundle: Path, name: str, text: str) -> None:
    """Edit a file and its manifest entry, as a new export would."""
    (bundle / name).write_text(text, encoding="utf-8")
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"][name] = file_digest(bundle / name)
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
