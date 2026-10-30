import importlib.util
import json
from datetime import date
from pathlib import Path

import pytest

from app.domain.errors import ConfigError
from app.satellite.config import load_imaging_config
from app.satellite.ndvi import compute_ndvi, zone_ndvi
from app.satellite.scenes import ImageryLoader, load_scene
from tests.conftest import CONFIG_DIR, SATELLITE_DIR

DEMO_FARM = (2.93, -75.28)
DAY = date(2026, 10, 28)


def _scene(tmp_path: Path, name: str = "s1", overrides: dict[str, object] | None = None) -> Path:
    body: dict[str, object] = {
        "acquired_on": "2026-10-20",
        "latitude": 2.95,
        "longitude": -75.3,
        "synthetic": True,
        "zones": {"Zona 1": [0, 0, 1, 1]},
        "red": [[0.05, 0.05]],
        "nir": [[0.45, 0.45]],
    }
    body.update(overrides or {})
    folder = tmp_path / name
    folder.mkdir()
    (folder / "scene.json").write_text(json.dumps(body), encoding="utf-8")
    (folder / "rgb.png").write_bytes(b"\x89PNG")
    return folder / "scene.json"


def test_the_shipped_scene_matches_its_readme() -> None:
    scene = ImageryLoader.from_directory(SATELLITE_DIR).latest(*DEMO_FARM, DAY)
    threshold = load_imaging_config(CONFIG_DIR / "imaging.yaml").low_ndvi_threshold

    assert scene is not None and scene.synthetic
    ndvi = compute_ndvi(scene.red, scene.nir)
    zone_1 = zone_ndvi(ndvi, scene.zones["Zona 1"], threshold)
    zone_2 = zone_ndvi(ndvi, scene.zones["Zona 2"], threshold)
    assert zone_1.mean is not None and zone_1.mean > threshold
    assert zone_2.mean is not None and zone_2.mean < threshold
    assert scene.rgb_png().startswith(b"\x89PNG")


def test_the_newest_scene_on_or_before_the_day_is_used(tmp_path: Path) -> None:
    _scene(tmp_path, "old", {"acquired_on": "2026-10-10"})
    _scene(tmp_path, "new", {"acquired_on": "2026-10-20"})
    _scene(tmp_path, "future", {"acquired_on": "2026-10-30"})
    loader = ImageryLoader.from_directory(tmp_path)

    found = loader.latest(*DEMO_FARM, DAY)

    assert found is not None and found.scene_id == "new"


def test_no_scene_before_the_day_or_near_the_plot(tmp_path: Path) -> None:
    _scene(tmp_path)
    loader = ImageryLoader.from_directory(tmp_path)

    assert loader.latest(*DEMO_FARM, date(2026, 10, 1)) is None
    assert loader.latest(4.6, -74.1, DAY) is None
    assert loader.latest(4.6, -75.3, DAY) is None  # far in latitude only
    assert loader.latest(2.95, -74.1, DAY) is None  # far in longitude only


def test_a_missing_directory_means_no_scenes(tmp_path: Path) -> None:
    assert ImageryLoader.from_directory(tmp_path / "none").latest(*DEMO_FARM, DAY) is None


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"nir": [[0.45]]}, "same shape"),
        ({"red": [[0.05, 1.5]]}, r"within \[0, 1\]"),
        ({"zones": {"Zona 1": [0, 0, 2, 1]}}, "not a box inside"),
        ({"zones": {}}, "zones"),
    ],
)
def test_a_malformed_scene_is_refused(
    tmp_path: Path, overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ConfigError, match=message):
        load_scene(_scene(tmp_path, overrides=overrides))


def test_a_scene_without_its_image_is_refused(tmp_path: Path) -> None:
    path = _scene(tmp_path)
    (path.parent / "rgb.png").unlink()

    with pytest.raises(ConfigError, match=r"rgb\.png is missing"):
        load_scene(path)


def test_the_generator_is_deterministic(tmp_path: Path) -> None:
    """Running the script again reproduces the shipped files byte for byte."""
    script = Path(__file__).resolve().parents[3] / "scripts" / "generate_demo_scene.py"
    spec = importlib.util.spec_from_file_location("generate_demo_scene", script)
    assert spec is not None and spec.loader is not None
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)

    generator.write_scene(tmp_path)

    shipped = SATELLITE_DIR / "neiva-2026-10-28"
    assert (tmp_path / "scene.json").read_bytes() == (shipped / "scene.json").read_bytes()
    assert (tmp_path / "rgb.png").read_bytes() == (shipped / "rgb.png").read_bytes()
