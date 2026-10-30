"""Segmentation as boxes, and the share of a zone they cover (§4.9, D059).

SAM 3.1 answers with special tokens, one box per match:
    <0f>0<|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..|><|mask;...|>,1<|box;...|>...
Only the boxes are used; the masks are not decoded. Empty output means no
match, which is a valid answer (0 %), not an error.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Protocol

from app.satellite.ndvi import NormalizedBox

_BOX = re.compile(r"(\d+)<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)\|>")


@dataclass(frozen=True)
class Box:
    """A box in image pixels, with the size of the image it was found in."""

    x1: int
    y1: int
    x2: int
    y2: int
    width: int
    height: int

    def normalized(self) -> tuple[float, float, float, float]:
        return (
            self.x1 / self.width,
            self.y1 / self.height,
            self.x2 / self.width,
            self.y2 / self.height,
        )


class SegmentationUnavailableError(Exception):
    """The segmentation service could not answer. The imaging value stays unknown."""


class SegmentationProvider(Protocol):
    def segment(self, image_png: bytes, prompt: str) -> tuple[Box, ...]: ...


class MalformedSegmentationError(ValueError):
    """A box that cannot be right: outside its image, or empty."""


def parse_boxes(output_text: str) -> tuple[Box, ...]:
    boxes = []
    for match in _BOX.finditer(output_text):
        x1, y1, x2, y2, width, height = (int(v) for v in match.groups()[1:])
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise MalformedSegmentationError(f"box outside its image: {match.group(0)}")
        boxes.append(Box(x1, y1, x2, y2, width, height))
    return tuple(boxes)


def covered_pct(boxes: Sequence[Box], area: NormalizedBox) -> float:
    """% of `area` covered by the union of the boxes. Overlaps count once.

    Exact, by cutting the plane at every box edge: each cell is either fully
    inside a box or not.
    """
    clipped = [
        (max(x1, area.x1), max(y1, area.y1), min(x2, area.x2), min(y2, area.y2))
        for x1, y1, x2, y2 in (box.normalized() for box in boxes)
    ]
    inside = [(x1, y1, x2, y2) for x1, y1, x2, y2 in clipped if x1 < x2 and y1 < y2]
    xs = sorted({area.x1, area.x2, *(b[0] for b in inside), *(b[2] for b in inside)})
    ys = sorted({area.y1, area.y2, *(b[1] for b in inside), *(b[3] for b in inside)})
    covered = sum(
        (right - left) * (bottom - top)
        for left, right in pairwise(xs)
        for top, bottom in pairwise(ys)
        if any(b[0] <= left and right <= b[2] and b[1] <= top and bottom <= b[3] for b in inside)
    )
    zone = (area.x2 - area.x1) * (area.y2 - area.y1)
    return round(100 * covered / zone, 1)


class MockSegmentation:
    """Fixed boxes for every image; records each call."""

    def __init__(self, boxes: Sequence[Box] = ()) -> None:
        self._boxes = tuple(boxes)
        self.calls: list[tuple[bytes, str]] = []

    def segment(self, image_png: bytes, prompt: str) -> tuple[Box, ...]:
        self.calls.append((image_png, prompt))
        return self._boxes
