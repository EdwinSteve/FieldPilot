"""The stages in order, each skipped when its output already exists (README §10).

`python -m fieldpilot_planner all` runs everything; any stage can run alone.
A stage whose output exists is skipped unless `--force` names it, so an
interrupted run continues where it stopped.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from fieldpilot_planner.build import clean, download, http_for
from fieldpilot_planner.config import PipelineConfig, load_pipeline
from fieldpilot_planner.crops import CropCard, load_crops
from fieldpilot_planner.dataset import CleanDataset
from fieldpilot_planner.oracle.labels import LabelSet, build_labels, sowing_years
from fieldpilot_planner.outputs import from_network
from fieldpilot_planner.paths import Paths
from fieldpilot_planner.points import read_points, select_points, write_points
from fieldpilot_planner.sources.datos_gov import fetch_eva

log = logging.getLogger(__name__)
STAGES = (
    "env",
    "points",
    "download",
    "clean",
    "labels",
    "tune",
    "train",
    "evaluate",
    "holdout",
    "export",
)
DEFAULT_ALL = (
    "env",
    "download",
    "clean",
    "labels",
    "tune",
    "train",
    "evaluate",
    "holdout",
    "export",
)


@dataclass
class Pipeline:
    paths: Paths
    run_name: str
    force: frozenset[str] = frozenset()
    config: PipelineConfig = field(init=False)
    crops: list[CropCard] = field(init=False)

    def __post_init__(self) -> None:
        self.config = load_pipeline(self.paths.configs / "pipeline.yaml")
        self.crops = list(load_crops(self.paths.configs / "crops.yaml"))

    @property
    def run_dir(self) -> Path:
        return self.paths.runs / self.run_name

    def run(self, stages: tuple[str, ...]) -> None:
        for stage in stages:
            log.info("=== stage %s ===", stage)
            getattr(self, f"stage_{stage}")()

    # --- data -----------------------------------------------------------------

    def stage_env(self) -> None:
        from fieldpilot_planner.env import check_environment  # noqa: PLC0415 - needs torch

        if not check_environment():
            raise SystemExit("the GPU is not usable; fix the environment before training")

    def stage_points(self) -> None:
        if self.paths.points_csv.exists() and "points" not in self.force:
            log.info("points.csv is versioned; skipping (use --force points to rebuild)")
            return
        points = select_points(http_for(self.paths), self.crops, self.config)
        write_points(self.paths.points_csv, points)
        log.info("%d points written", len(points))

    def stage_download(self) -> None:
        download(self.paths, read_points(self.paths.points_csv), self.crops, self.config)

    def stage_clean(self) -> None:
        if (self.paths.clean / "dataset.npz").exists() and "clean" not in self.force:
            log.info("clean dataset exists; skipping")
            return
        clean(self.paths, read_points(self.paths.points_csv), self.config).save(self.paths.clean)

    def stage_labels(self) -> None:
        if (self.paths.labels / "labels.npz").exists() and "labels" not in self.force:
            log.info("labels exist; skipping")
            return
        build_labels(CleanDataset.load(self.paths.clean), self.crops, self.config).save(
            self.paths.labels
        )

    # --- training -------------------------------------------------------------

    def _session(self, holdout: bool = False) -> "Session":
        return Session.open(self, holdout)

    def stage_tune(self) -> None:
        session = self._session()
        best = session.tune()
        (self.run_dir / "best_trial.json").write_text(json.dumps(best, indent=1), encoding="utf-8")

    def stage_train(self) -> None:
        self._session().train_final()

    def stage_evaluate(self) -> None:
        self._session().evaluate()

    def stage_holdout(self) -> None:
        self._session(holdout=True).holdout()

    def stage_export(self) -> None:
        stamp = datetime.now().astimezone().date().isoformat()
        self._session().export(self.paths.models / f"planner-{stamp}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


class Session:
    """Everything the training stages share: data on the device, splits, config."""

    def __init__(self, pipe: Pipeline, holdout: bool) -> None:
        import torch  # noqa: PLC0415, F401 - fail early, with a clear error, if torch is missing

        from fieldpilot_planner.train import Samples, load_train_config, pick_device  # noqa: PLC0415
        from fieldpilot_planner.training_data import (  # noqa: PLC0415
            fit_normalization,
            sample_contexts,
            standard_splits,
            to_device,
        )

        self.pipe = pipe
        self.cfg = load_train_config(pipe.paths.configs / "train.yaml")
        self.data = CleanDataset.load(pipe.paths.clean)
        self.labels = LabelSet.load(pipe.paths.labels)
        self.device = pick_device()
        splits = standard_splits(self.data, pipe.config, holdout)
        years = sowing_years(self.data, self.labels.sow)
        self.samples = {
            k: Samples.from_mask(s.mask(years, self.labels.valid)) for k, s in splits.items()
        }
        contexts = sample_contexts(self.data, self.labels.sow)
        self.norm = fit_normalization(self.data, self.labels, contexts, splits["train"], pipe.crops)
        self.dev = to_device(self.data, self.labels, pipe.crops, self.norm, contexts, self.device)
        log.info("samples: %s", {k: len(v) for k, v in self.samples.items()})

    @classmethod
    def open(cls, pipe: Pipeline, holdout: bool) -> "Session":
        return cls(pipe, holdout)

    def _best_trial(self) -> dict[str, Any] | None:
        path = self.pipe.run_dir / "best_trial.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def _tuned(self) -> tuple[Any, dict[str, Any]]:
        best = self._best_trial()
        if best is None:
            return self.cfg, {}
        model = {**best["model"], "dilations": tuple(best["model"]["dilations"])}
        return replace(self.cfg, optim=replace(self.cfg.optim, **best["optim"])), model

    def tune(self) -> dict[str, Any]:
        from fieldpilot_planner.train import tune  # noqa: PLC0415

        fast = replace(self.cfg, runtime=replace(self.cfg.runtime, deterministic_final=False))
        return tune(fast, self.dev, self.device, self.samples["train"], self.samples["validation"],
                    self.pipe.run_dir / "tune")  # fmt: skip

    def train_final(self) -> None:
        """Early stopping on validation, then a refit on train + validation for that many epochs."""
        from fieldpilot_planner.train import Trainer  # noqa: PLC0415

        cfg, model = self._tuned()
        main = Trainer(cfg, self.dev, self.device, self.pipe.run_dir / "main", model)
        result = main.fit(self.samples["train"], self.samples["validation"])
        log.info("main run: best epoch %d, val %.5f", result.best_epoch, result.best_val_loss)
        refit = Trainer(cfg, self.dev, self.device, self.pipe.run_dir / "refit", model)
        refit.fit(self.samples["train+validation"], None, epochs=max(result.best_epoch, 1))

    def _final_model(self) -> Any:
        from fieldpilot_planner.train import Trainer  # noqa: PLC0415

        cfg, model = self._tuned()
        return Trainer(cfg, self.dev, self.device, self.pipe.run_dir / "refit", model).load_best()

    def _scores(self, model: Any, test_key: str = "test") -> dict[str, dict[str, float]]:
        from fieldpilot_planner.evaluate import from_b0, from_b1, score  # noqa: PLC0415
        from fieldpilot_planner.train import predict  # noqa: PLC0415

        test = self.samples[test_key]
        net = from_network(predict(model, self.dev, test, self.device, self.cfg.runtime.precision))
        return {
            "network": score(net, self.labels, test),
            "b0_climatology": score(from_b0(self.labels, test), self.labels, test),
            "b1_history": score(
                from_b1(self.data, self.labels, self.samples["train"], test), self.labels, test
            ),
        }

    def evaluate(self) -> None:
        from fieldpilot_planner.evaluate import adopted, eva_spearman  # noqa: PLC0415
        from fieldpilot_planner.train import predict  # noqa: PLC0415

        model = self._final_model()
        scores = self._scores(model)
        test = self.samples["test"]
        net = from_network(predict(model, self.dev, test, self.device, self.cfg.runtime.precision))
        eva = fetch_eva(
            http_for(self.pipe.paths), [n for c in self.pipe.crops for n in c.eva_names]
        )
        span = self.pipe.config.test
        metrics = {
            "test_years": f"{span.first}-{span.last}",
            "test": scores,
            "adopted": adopted(scores["network"], scores["b0_climatology"]),
            "eva_spearman": eva_spearman(self.data, self.labels, self.pipe.crops, test, net, eva),
        }
        self._write_metrics(metrics)
        log.info("test metrics: %s", json.dumps(metrics, indent=1))

    def holdout(self) -> None:
        """Train without the held-out departments; test on them only (README §7.3)."""
        from fieldpilot_planner.train import Trainer  # noqa: PLC0415

        cfg, model = self._tuned()
        trainer = Trainer(cfg, self.dev, self.device, self.pipe.run_dir / "holdout", model)
        trainer.fit(self.samples["train"], self.samples["validation"])
        scores = self._scores(trainer.load_best())
        self._write_metrics({"holdout": scores})
        log.info("holdout metrics: %s", json.dumps(scores, indent=1))

    def _write_metrics(self, update: dict[str, Any]) -> None:
        path = self.pipe.run_dir / "metrics.json"
        current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        path.write_text(json.dumps({**current, **update}, indent=1), encoding="utf-8")

    def export(self, out_dir: Path) -> None:
        from fieldpilot_planner.export import write_bundle  # noqa: PLC0415
        from fieldpilot_planner.train import Samples  # noqa: PLC0415

        metrics = json.loads((self.pipe.run_dir / "metrics.json").read_text(encoding="utf-8"))
        test = self.samples["test"]
        few = Samples(test.p[:64], test.s[:64])
        import torch  # noqa: PLC0415

        weather, clim, static, prior, _ = self.dev.batch(
            torch.as_tensor(few.p, device=self.device), torch.as_tensor(few.s, device=self.device)
        )
        paths = self.pipe.paths
        data_manifest = {
            name: sha256_file(path)
            for name, path in (
                ("points.csv", paths.points_csv),
                ("crops.yaml", paths.configs / "crops.yaml"),
                ("pipeline.yaml", paths.configs / "pipeline.yaml"),
                ("train.yaml", paths.configs / "train.yaml"),
                ("dataset.npz", paths.clean / "dataset.npz"),
                ("labels.npz", paths.labels / "labels.npz"),
            )
        }  # fmt: skip
        manifest = write_bundle(
            out_dir, self._final_model(), (weather, clim, static, self.dev.crops, prior), self.norm,
            self.pipe.crops, paths.configs / "crops.yaml", metrics, data_manifest,
        )  # fmt: skip
        log.info(
            "bundle written to %s (ONNX parity %.2e)", out_dir, manifest["onnx_parity_max_abs"]
        )
