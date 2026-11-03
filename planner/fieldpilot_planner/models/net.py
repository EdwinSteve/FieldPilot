"""CropPlannerNet (README §7.2): one site-date encoding, crossed with every crop card."""

from collections.abc import Callable
from dataclasses import dataclass

import torch
from torch import Tensor, nn
from torch.nn import functional as F


@dataclass(frozen=True)
class NetConfig:
    weather_in: int
    clim_in: int
    static_in: int
    crop_in: int
    prior_in: int = 5  # B0, the oracle on climatology, per crop (features.prior_features)
    weather_channels: int = 64
    dilations: tuple[int, ...] = (1, 2, 4, 8, 16, 32)
    clim_channels: int = 32
    static_hidden: int = 128
    embedding: int = 256
    head_hidden: int = 128
    dropout: float = 0.1


class ResidualDilatedBlock(nn.Module):
    def __init__(self, channels: int, dilation: int, dropout: float) -> None:
        super().__init__()
        self.conv1 = nn.Conv1d(channels, channels, 3, padding=dilation, dilation=dilation)
        self.conv2 = nn.Conv1d(channels, channels, 1)
        self.norm = nn.GroupNorm(8, channels)
        self.drop = nn.Dropout(dropout)

    def forward(self, x: Tensor) -> Tensor:
        return x + self.drop(self.conv2(F.gelu(self.norm(self.conv1(x)))))


class AttentionPool(nn.Module):
    """Learned weighting of the time steps: which days of the past year matter."""

    def __init__(self, channels: int) -> None:
        super().__init__()
        self.score = nn.Conv1d(channels, 1, 1)

    def forward(self, x: Tensor) -> Tensor:
        weights = torch.softmax(self.score(x), dim=-1)
        return (x * weights).sum(dim=-1)


class CropPlannerNet(nn.Module):
    """Outputs per (site-date, crop); quantiles are ordered by construction."""

    def __init__(self, cfg: NetConfig) -> None:
        super().__init__()
        wc, cc = cfg.weather_channels, cfg.clim_channels
        self.weather_stem = nn.Conv1d(cfg.weather_in, wc, 1)
        self.weather_blocks = nn.Sequential(
            *(ResidualDilatedBlock(wc, d, cfg.dropout) for d in cfg.dilations)
        )
        self.weather_pool = AttentionPool(wc)
        self.clim = nn.Sequential(
            nn.Conv1d(cfg.clim_in, cc, 5, stride=2, padding=2), nn.GELU(),
            nn.Conv1d(cc, cc, 5, stride=2, padding=2), nn.GELU(),
            nn.Conv1d(cc, cc, 5, stride=2, padding=2), nn.GELU(),
        )  # fmt: skip
        self.static = nn.Sequential(
            nn.Linear(cfg.static_in, cfg.static_hidden), nn.GELU(),
            nn.Linear(cfg.static_hidden, cfg.static_hidden), nn.GELU(),
        )  # fmt: skip
        self.site = nn.Sequential(
            nn.Linear(wc + cc + cfg.static_hidden, cfg.embedding), nn.GELU(),
            nn.Dropout(cfg.dropout), nn.LayerNorm(cfg.embedding),
        )  # fmt: skip
        self.crop = nn.Sequential(
            nn.Linear(cfg.crop_in, cfg.embedding), nn.GELU(),
            nn.Linear(cfg.embedding, 2 * cfg.embedding),
        )  # fmt: skip
        self.trunk = nn.Sequential(
            nn.Linear(cfg.embedding + cfg.prior_in, cfg.head_hidden), nn.GELU(),
            nn.Dropout(cfg.dropout),
            nn.Linear(cfg.head_hidden, cfg.head_hidden), nn.GELU(),
        )  # fmt: skip
        # rel_yield (3) + success logit (1) + log1p irrigation (3) + heat, cold fractions (2)
        self.head = nn.Linear(cfg.head_hidden, 9)

    def forward(
        self, weather: Tensor, clim: Tensor, static: Tensor, crops: Tensor, prior: Tensor
    ) -> Tensor:
        """weather [B, Cw, 365], clim [B, Cc, 210], static [B, Fs], crops [C, Fc],
        prior [B, C, 5] -> [B, C, 9].

        The prior is B0: what the oracle gives on the climatology. The network
        starts from that physical expectation and learns what the climatology
        cannot see (ENSO, soil moisture at sowing, the recent past).

        Output columns: rel_yield p10, p50, p90; success logit; log1p irrigation
        p10, p50, p90; heat-day fraction; cold-day fraction.
        """
        w = self.weather_pool(self.weather_blocks(self.weather_stem(weather)))
        c = self.clim(clim).mean(dim=-1)
        site = self.site(torch.cat([w, c, self.static(static)], dim=-1))  # [B, E]
        gamma, beta = self.crop(crops).chunk(2, dim=-1)  # [C, E] each (FiLM)
        crossed = site[:, None, :] * (1 + gamma[None]) + beta[None]  # [B, C, E]
        h = self.trunk(torch.cat([crossed, prior], dim=-1))  # [B, C, H]
        raw = self.head(h)
        return torch.cat(
            [
                _ordered(raw[..., 0:3], torch.sigmoid),
                raw[..., 3:4],
                _ordered(raw[..., 4:7], lambda t: t),
                torch.sigmoid(raw[..., 7:9]),
            ],
            dim=-1,
        )


def _ordered(raw: Tensor, center: Callable[[Tensor], Tensor]) -> Tensor:
    """p10 <= p50 <= p90: the median plus two non-negative gaps."""
    mid = center(raw[..., 1:2])
    return torch.cat(
        [mid - F.softplus(raw[..., 0:1]), mid, mid + F.softplus(raw[..., 2:3])], dim=-1
    )
