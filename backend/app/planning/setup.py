"""Pick what serves the plan: the adopted network, else B0 (D079, D081)."""

from pathlib import Path

from fieldpilot_planner.config import load_pipeline
from fieldpilot_planner.crops import load_crops

from app.domain.errors import ConfigError
from app.planning.bundle import load_bundle, newest_bundle
from app.planning.climatology import ClimatologyRecommender
from app.planning.onnx import OnnxRecommender
from app.planning.ports import CropRecommender


def build_recommender(planner_dir: Path, bundle_dir: Path | None) -> CropRecommender:
    """PLANNER_BUNDLE, else the newest bundle; B0 when there is none or it was not adopted.

    The success threshold and spin-up come from the pipeline the bundle was trained with.
    """
    configs = planner_dir / "configs"
    try:
        pipeline = load_pipeline(configs / "pipeline.yaml")
    except (OSError, KeyError, ValueError) as error:
        raise ConfigError(f"planner pipeline.yaml: {error}") from error
    threshold, spinup = pipeline.success_rel_yield, pipeline.spinup_days
    chosen = bundle_dir or newest_bundle(planner_dir / "models")
    if chosen is None:
        return ClimatologyRecommender(load_crops(configs / "crops.yaml"), threshold, spinup)
    bundle = load_bundle(chosen)
    if not bundle.adopted:
        return ClimatologyRecommender(bundle.crops, threshold, spinup)
    return OnnxRecommender(bundle, threshold, spinup)
