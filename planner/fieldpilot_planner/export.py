"""Stage `export`: the model bundle the backend serves (README §8.4)."""

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
import torch

from fieldpilot_planner.crops import CropCard
from fieldpilot_planner.features import (
    CLIM_CHANNELS,
    STATIC_FEATURES,
    WEATHER_CHANNELS,
    Normalization,
)

OPSET = 17
PARITY_TOLERANCE = 1e-4
INPUTS = ("weather", "clim", "static", "crops", "prior")
OUTPUT = "outputs"


def export_onnx(model: torch.nn.Module, sample: tuple[torch.Tensor, ...], path: Path) -> None:
    model = model.float().cpu().eval()
    torch.onnx.export(
        model,
        tuple(t.float().cpu() for t in sample),
        str(path),
        input_names=list(INPUTS),
        output_names=[OUTPUT],
        dynamic_axes={
            "weather": {0: "batch"},
            "clim": {0: "batch"},
            "static": {0: "batch"},
            "crops": {0: "crops"},
            "prior": {0: "batch", 1: "crops"},
            OUTPUT: {0: "batch", 1: "crops"},
        },
        opset_version=OPSET,
        dynamo=False,
    )


def parity(model: torch.nn.Module, sample: tuple[torch.Tensor, ...], path: Path) -> float:
    """Largest absolute difference between PyTorch and ONNX Runtime on the same inputs."""
    model = model.float().cpu().eval()
    inputs = tuple(t.float().cpu() for t in sample)
    with torch.no_grad():
        expected = model(*inputs).numpy()
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    got = session.run(None, {name: t.numpy() for name, t in zip(INPUTS, inputs, strict=True)})[0]
    return float(np.abs(expected - got).max())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_bundle(
    out_dir: Path,
    model: torch.nn.Module,
    sample: tuple[torch.Tensor, ...],
    norm: Normalization,
    crops: Sequence[CropCard],
    crops_yaml: Path,
    metrics: dict[str, Any],
    data_manifest: dict[str, str],
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = out_dir / "model.onnx"
    export_onnx(model, sample, onnx_path)
    difference = parity(model, sample, onnx_path)
    if difference > PARITY_TOLERANCE:
        raise RuntimeError(f"ONNX parity failed: max difference {difference:.2e}")
    norm.save(out_dir / "normalization.json")
    (out_dir / "crops.yaml").write_bytes(crops_yaml.read_bytes())
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=1), encoding="utf-8")
    (out_dir / "MODEL_CARD.md").write_text(model_card(metrics, crops, difference), encoding="utf-8")
    manifest = {
        "files": {
            p.name: sha256(p) for p in sorted(out_dir.iterdir()) if p.name != "manifest.json"
        },
        "inputs": {
            "weather": list(WEATHER_CHANNELS),
            "clim": list(CLIM_CHANNELS),
            "static": list(STATIC_FEATURES),
            "crops": [c.crop for c in crops],
        },
        "data": data_manifest,
        "onnx_parity_max_abs": difference,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest


def _table(rows: dict[str, dict[str, float]]) -> str:
    keys = list(next(iter(rows.values())))
    lines = ["| Model | " + " | ".join(keys) + " |", "|---" * (len(keys) + 1) + "|"]
    lines += [
        f"| {name} | " + " | ".join(str(v[k]) for k in keys) + " |" for name, v in rows.items()
    ]
    return "\n".join(lines)


def model_card(metrics: dict[str, Any], crops: Sequence[CropCard], parity_diff: float) -> str:
    test = metrics["test"]
    verdict = (
        "**Adopted:** it beats the climatology oracle (B0) on pinball loss and NDCG@3."
        if metrics["adopted"]
        else "**Not adopted:** it does not beat B0 on both metrics; the backend serves B0."
    )
    return f"""# CropPlannerNet model card

{verdict}

- **Task:** rainfed relative yield (p10/p50/p90), P(relative yield >= 0.6), irrigation
  need and stress days for {len(crops)} crops: {", ".join(c.crop for c in crops)}.
- **Labels:** an oracle of published FAO models (FAO-56 water balance, FAO-33 Ky,
  ECOCROP ranges) run on NASA POWER weather, 1981-2025 (planner/README.md §6).
- **Not calibrated against real yields.** The EVA check below is the only comparison
  with reality; the crop parameters have not been reviewed by an agronomist.
- **ONNX parity:** max |PyTorch - ONNX Runtime| = {parity_diff:.2e}.

## Test split ({metrics["test_years"]})

{_table(test)}

## Spatial holdout (Huila never seen in training)

{_table(metrics["holdout"]) if metrics.get("holdout") else "Not run."}

## Spearman with EVA municipal yield anomalies (test years)

{json.dumps(metrics.get("eva_spearman", {}), indent=1)}
"""
