"""Stages `train` and `tune` (README §8): resumable, bf16 on the GPU, early stopping."""

import json
import logging
import math
import platform
import random
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, cast

import numpy as np
import numpy.typing as npt
import torch
from torch import Tensor
from torch.nn import functional as F

from fieldpilot_planner.config import load_yaml
from fieldpilot_planner.metrics import QUANTILES
from fieldpilot_planner.models.net import CropPlannerNet, NetConfig
from fieldpilot_planner.training_data import DeviceData

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class OptimConfig:
    batch_size: int = 1024
    lr: float = 1e-3
    weight_decay: float = 1e-2
    warmup_fraction: float = 0.1
    grad_clip: float = 1.0
    max_epochs: int = 40
    patience: int = 5


@dataclass(frozen=True)
class LossWeights:
    rel_yield: float = 1.0
    success: float = 0.5
    irrigation: float = 0.5
    stress: float = 0.2


@dataclass(frozen=True)
class RuntimeConfig:
    precision: str = "bf16"
    compile: str = "auto"
    seed: int = 7
    deterministic_final: bool = True


@dataclass(frozen=True)
class TrainConfig:
    model: dict[str, Any]
    optim: OptimConfig
    loss: LossWeights
    runtime: RuntimeConfig
    tuning: dict[str, Any]


def load_train_config(path: Path) -> TrainConfig:
    raw = load_yaml(path)
    model = dict(raw["model"])
    model["dilations"] = tuple(model["dilations"])
    return TrainConfig(
        model=model,
        optim=OptimConfig(**raw["optim"]),
        loss=LossWeights(**raw["loss_weights"]),
        runtime=RuntimeConfig(**raw["runtime"]),
        tuning=raw["tuning"],
    )


def pinball(pred: Tensor, target: Tensor) -> Tensor:
    """pred [..., 3] for QUANTILES, target [...]."""
    q = torch.tensor(QUANTILES, device=pred.device, dtype=pred.dtype)
    diff = target[..., None] - pred
    return torch.maximum(q * diff, (q - 1) * diff).mean()


def loss_fn(out: Tensor, target: Tensor, w: LossWeights) -> Tensor:
    out = out.float()
    return (
        w.rel_yield * pinball(out[..., 0:3], target[..., 0])
        + w.success * F.binary_cross_entropy_with_logits(out[..., 3], target[..., 1])
        + w.irrigation * pinball(out[..., 4:7], target[..., 2])
        + w.stress * F.huber_loss(out[..., 7:9], target[..., 3:5], delta=0.1)
    )


def seed_everything(seed: int, deterministic: bool) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.backends.cudnn.benchmark = not deterministic
    torch.backends.cudnn.deterministic = deterministic


def pick_device() -> torch.device:
    if torch.cuda.is_available():
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        return torch.device("cuda")
    log.warning("no CUDA device: training on the CPU will be very slow")
    return torch.device("cpu")


def _autocast(device: torch.device, precision: str) -> torch.autocast:
    enabled = device.type == "cuda" and precision == "bf16" and torch.cuda.is_bf16_supported()
    return torch.autocast(device_type=device.type, dtype=torch.bfloat16, enabled=enabled)


def _maybe_compile(model: torch.nn.Module, mode: str) -> torch.nn.Module:
    if mode == "off" or (mode == "auto" and platform.system() == "Windows"):
        return model  # Triton, which torch.compile needs on the GPU, is not on Windows
    try:
        return cast("torch.nn.Module", torch.compile(model))
    except Exception:  # any compile failure falls back to eager mode
        log.warning("torch.compile unavailable; running in eager mode")
        return model


@dataclass(frozen=True)
class Samples:
    p: npt.NDArray[np.int64]
    s: npt.NDArray[np.int64]

    @classmethod
    def from_mask(cls, mask: npt.NDArray[np.bool_]) -> "Samples":
        p, s = np.nonzero(mask)
        return cls(p.astype(np.int64), s.astype(np.int64))

    def __len__(self) -> int:
        return len(self.p)


@dataclass
class RunResult:
    best_val_loss: float
    best_epoch: int
    epochs_run: int
    seconds: float


def build_model(
    cfg: TrainConfig, data: DeviceData, model_overrides: dict[str, Any]
) -> CropPlannerNet:
    params = {**cfg.model, **model_overrides}
    net_cfg = NetConfig(
        weather_in=data.weather.shape[-1], clim_in=data.clim.shape[-1],
        static_in=data.site.shape[-1] + data.contexts.shape[-1], crop_in=data.crops.shape[-1],
        **params,
    )  # fmt: skip
    return CropPlannerNet(net_cfg)


@torch.no_grad()
def evaluate_loss(
    model: torch.nn.Module,
    data: DeviceData,
    samples: Samples,
    cfg: TrainConfig,
    device: torch.device,
) -> float:
    model.eval()
    total, count = 0.0, 0
    for start in range(0, len(samples), 4096):
        p = torch.as_tensor(samples.p[start : start + 4096], device=device)
        s = torch.as_tensor(samples.s[start : start + 4096], device=device)
        weather, clim, static, prior, target = data.batch(p, s)
        with _autocast(device, cfg.runtime.precision):
            out = model(weather, clim, static, data.crops, prior)
        total += float(loss_fn(out, target, cfg.loss)) * len(p)
        count += len(p)
    return total / max(count, 1)


@torch.no_grad()
def predict(
    model: torch.nn.Module, data: DeviceData, samples: Samples, device: torch.device, precision: str
) -> npt.NDArray[np.float32]:
    """[N, C, 9] in the network's output layout (models/net.py)."""
    model.eval()
    chunks = []
    for start in range(0, len(samples), 4096):
        p = torch.as_tensor(samples.p[start : start + 4096], device=device)
        s = torch.as_tensor(samples.s[start : start + 4096], device=device)
        weather, clim, static, prior, _ = data.batch(p, s)
        with _autocast(device, precision):
            chunks.append(model(weather, clim, static, data.crops, prior).float().cpu().numpy())
    return np.concatenate(chunks).astype(np.float32)


class Trainer:
    """One training run, resumable from `run_dir/last.pt` after a power cut."""

    def __init__(
        self,
        cfg: TrainConfig,
        data: DeviceData,
        device: torch.device,
        run_dir: Path,
        model_overrides: dict[str, Any] | None = None,
    ) -> None:
        self.cfg, self.data, self.device, self.run_dir = cfg, data, device, run_dir
        self.overrides = model_overrides or {}
        run_dir.mkdir(parents=True, exist_ok=True)

    def fit(self, train: Samples, val: Samples | None, epochs: int | None = None) -> RunResult:
        """With `val`, early stopping keeps the best epoch; without it, runs `epochs` exactly."""
        cfg, opt_cfg = self.cfg, self.cfg.optim
        seed_everything(cfg.runtime.seed, cfg.runtime.deterministic_final)
        model = build_model(cfg, self.data, self.overrides).to(self.device)
        max_epochs = epochs or opt_cfg.max_epochs
        steps = max_epochs * math.ceil(len(train) / opt_cfg.batch_size)
        self._total_steps = steps
        optimizer = torch.optim.AdamW(
            model.parameters(), lr=opt_cfg.lr, weight_decay=opt_cfg.weight_decay
        )
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer, max_lr=opt_cfg.lr, total_steps=steps, pct_start=opt_cfg.warmup_fraction
        )
        state = {"epoch": 0, "best_val": math.inf, "best_epoch": 0, "bad": 0}
        resumed = self._resume(model, optimizer, scheduler, state)
        if resumed:
            log.info("resumed %s at epoch %d", self.run_dir.name, state["epoch"])
        compiled = _maybe_compile(model, cfg.runtime.compile)
        started = time.monotonic()
        while state["epoch"] < max_epochs and state["bad"] < opt_cfg.patience:
            train_loss = self._epoch(compiled, optimizer, scheduler, train, int(state["epoch"]))
            state["epoch"] += 1
            val_loss = (
                evaluate_loss(compiled, self.data, val, cfg, self.device) if val else train_loss
            )
            improved = val_loss < state["best_val"] - 1e-5
            if improved:
                state.update(best_val=val_loss, best_epoch=state["epoch"], bad=0)
                torch.save(model.state_dict(), self.run_dir / "best.pt")
            elif val is not None:
                state["bad"] += 1
            self._log_epoch(state, train_loss, val_loss)
            self._checkpoint(model, optimizer, scheduler, state)
        if val is None:  # a refit keeps its final weights
            torch.save(model.state_dict(), self.run_dir / "best.pt")
        return RunResult(
            float(state["best_val"]),
            int(state["best_epoch"]),
            int(state["epoch"]),
            time.monotonic() - started,
        )

    def load_best(self) -> CropPlannerNet:
        model = build_model(self.cfg, self.data, self.overrides).to(self.device)
        model.load_state_dict(torch.load(self.run_dir / "best.pt", map_location=self.device))
        return model

    def _epoch(
        self,
        model: torch.nn.Module,
        optimizer: torch.optim.Optimizer,
        scheduler: torch.optim.lr_scheduler.LRScheduler,
        train: Samples,
        epoch: int,
    ) -> float:
        model.train()
        gen = torch.Generator().manual_seed(self.cfg.runtime.seed * 1000 + epoch)
        order = torch.randperm(len(train), generator=gen).numpy()
        bs, total, count = self.cfg.optim.batch_size, 0.0, 0
        for start in range(0, len(order), bs):
            idx = order[start : start + bs]
            if len(idx) < 2:
                continue
            p = torch.as_tensor(train.p[idx], device=self.device)
            s = torch.as_tensor(train.s[idx], device=self.device)
            weather, clim, static, prior, target = self.data.batch(p, s)
            with _autocast(self.device, self.cfg.runtime.precision):
                out = model(weather, clim, static, self.data.crops, prior)
            loss = loss_fn(out, target, self.cfg.loss)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), self.cfg.optim.grad_clip)
            optimizer.step()
            if scheduler.last_epoch < self._total_steps - 1:  # OneCycle must not step past its end
                scheduler.step()
            total += float(loss) * len(idx)
            count += len(idx)
        return total / max(count, 1)

    def _log_epoch(self, state: dict[str, Any], train_loss: float, val_loss: float) -> None:
        line = {
            "epoch": state["epoch"],
            "train_loss": round(train_loss, 5),
            "val_loss": round(val_loss, 5),
            "best_epoch": state["best_epoch"],
        }
        log.info(
            "%s epoch %d train %.5f val %.5f",
            self.run_dir.name,
            state["epoch"],
            train_loss,
            val_loss,
        )
        with (self.run_dir / "history.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(line) + "\n")

    def _checkpoint(
        self,
        model: torch.nn.Module,
        optimizer: torch.optim.Optimizer,
        scheduler: torch.optim.lr_scheduler.LRScheduler,
        state: dict[str, Any],
    ) -> None:
        tmp = self.run_dir / "last.pt.part"
        torch.save(
            {
                "model": model.state_dict(),
                "optimizer": optimizer.state_dict(),
                "scheduler": scheduler.state_dict(),
                "state": state,
            },
            tmp,
        )
        tmp.replace(self.run_dir / "last.pt")

    def _resume(
        self,
        model: torch.nn.Module,
        optimizer: torch.optim.Optimizer,
        scheduler: torch.optim.lr_scheduler.LRScheduler,
        state: dict[str, Any],
    ) -> bool:
        path = self.run_dir / "last.pt"
        if not path.exists():
            return False
        saved = torch.load(path, map_location=self.device)
        model.load_state_dict(saved["model"])
        optimizer.load_state_dict(saved["optimizer"])
        scheduler.load_state_dict(saved["scheduler"])
        state.update(saved["state"])
        return True


def sample_trial(
    space: dict[str, Any], rng: random.Random
) -> tuple[dict[str, Any], dict[str, Any]]:
    """(model overrides, optimiser overrides) for one random-search trial (README §8.3)."""
    low, high = space["lr"]
    lr = math.exp(rng.uniform(math.log(low), math.log(high)))
    model = {
        "weather_channels": rng.choice(space["weather_channels"]),
        "dilations": tuple(rng.choice(space["dilations"])),
        "dropout": round(rng.uniform(*space["dropout"]), 3),
    }
    return model, {"lr": lr, "batch_size": rng.choice(space["batch_size"])}


def tune(
    cfg: TrainConfig,
    data: DeviceData,
    device: torch.device,
    train: Samples,
    val: Samples,
    out_dir: Path,
) -> dict[str, Any]:
    """Random search; finished trials are read back from trials.jsonl, so it resumes."""
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "trials.jsonl"
    done = (
        [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
        if log_path.exists()
        else []
    )
    rng = random.Random(cfg.runtime.seed)
    trials = [sample_trial(cfg.tuning["space"], rng) for _ in range(int(cfg.tuning["trials"]))]
    for i, (model_over, optim_over) in enumerate(trials):
        if any(t["trial"] == i for t in done):
            continue
        trial_cfg = replace(
            cfg, optim=replace(cfg.optim, max_epochs=int(cfg.tuning["epochs"]), **optim_over)
        )
        result = Trainer(trial_cfg, data, device, out_dir / f"trial_{i:02d}", model_over).fit(
            train, val
        )
        record = {
            "trial": i,
            "model": {**model_over, "dilations": list(model_over["dilations"])},
            "optim": optim_over,
            **asdict(result),
        }
        done.append(record)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        log.info("trial %d/%d val %.5f", i + 1, len(trials), result.best_val_loss)
    best = min(done, key=lambda t: t["best_val_loss"])
    log.info("best trial %d: val %.5f", best["trial"], best["best_val_loss"])
    return best
