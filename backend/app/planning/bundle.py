"""The trained planner bundle: found, checked against its manifest, and loaded (D081)."""

import json
from dataclasses import dataclass
from pathlib import Path

from fieldpilot_planner.crops import CropCard, load_crops
from fieldpilot_planner.features import Normalization
from fieldpilot_planner.manifest import changed_files

from app.domain.errors import ConfigError


@dataclass(frozen=True)
class PlannerBundle:
    id: str  # the folder name, e.g. planner-2026-11-03
    onnx_path: Path
    crops: tuple[CropCard, ...]
    norm: Normalization
    adopted: bool  # it beat B0 on the test split (metrics.json)


def newest_bundle(models_dir: Path) -> Path | None:
    """The last folder by name (planner-YYYY-MM-DD) that has a manifest."""
    if not models_dir.is_dir():
        return None
    found = sorted(p for p in models_dir.iterdir() if (p / "manifest.json").is_file())
    return found[-1] if found else None


def load_bundle(directory: Path) -> PlannerBundle:
    """Refuses a bundle whose files do not match the SHA-256 in its manifest."""
    name = directory.name
    try:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        changed = changed_files(directory, manifest["files"])
        crops = load_crops(directory / "crops.yaml")
        metrics = json.loads((directory / "metrics.json").read_text(encoding="utf-8"))
        adopted = bool(metrics["adopted"])
        norm = Normalization.load(directory / "normalization.json")
        crop_names = manifest["inputs"]["crops"]
    except (OSError, KeyError, ValueError) as error:
        raise ConfigError(f"planner bundle {name}: {error}") from error
    if changed:
        raise ConfigError(f"planner bundle {name}: {', '.join(changed)} do not match the manifest")
    if [c.crop for c in crops] != crop_names:
        raise ConfigError(f"planner bundle {name}: crops differ from the manifest")
    return PlannerBundle(name, directory / "model.onnx", crops, norm, adopted)
