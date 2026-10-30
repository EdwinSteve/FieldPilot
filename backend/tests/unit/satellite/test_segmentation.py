from pathlib import Path

import pytest

from app.satellite.ndvi import NormalizedBox
from app.satellite.scenes import load_scene
from app.satellite.segmentation import (
    Box,
    MalformedSegmentationError,
    MockSegmentation,
    covered_pct,
    parse_boxes,
)
from tests.conftest import SATELLITE_DIR

RECORDED = Path(__file__).resolve().parents[2] / "fixtures" / "sam" / "neiva_brown_patch.txt"
WHOLE = NormalizedBox(0, 0, 1, 1)


def _box(x1: int, y1: int, x2: int, y2: int) -> Box:
    return Box(x1, y1, x2, y2, 100, 100)


def test_the_recorded_sam_answer_parses_to_the_three_patches() -> None:
    boxes = parse_boxes(RECORDED.read_text(encoding="utf-8"))

    assert boxes == (
        Box(376, 126, 464, 214, 512, 256),
        Box(271, 161, 329, 219, 512, 256),
        Box(293, 33, 367, 107, 512, 256),
    )


def test_the_recorded_answer_covers_zone_2_only() -> None:
    scene = load_scene(SATELLITE_DIR / "neiva-2026-10-28" / "scene.json")
    boxes = parse_boxes(RECORDED.read_text(encoding="utf-8"))

    assert covered_pct(boxes, scene.zones["Zona 1"]) == 0.0
    assert covered_pct(boxes, scene.zones["Zona 2"]) == 25.3


def test_no_match_is_an_empty_answer_not_an_error() -> None:
    assert parse_boxes("") == ()
    assert parse_boxes("<0f>") == ()


@pytest.mark.parametrize(
    "token",
    [
        "0<|box;x1=10;y1=0;x2=120;y2=50;w=100;h=100|>",
        "0<|box;x1=50;y1=0;x2=50;y2=50;w=100;h=100|>",
    ],
)
def test_an_impossible_box_is_refused(token: str) -> None:
    with pytest.raises(MalformedSegmentationError, match="box outside its image"):
        parse_boxes(token)


def test_a_box_covering_the_zone_is_100() -> None:
    assert covered_pct([_box(0, 0, 100, 100)], WHOLE) == 100.0


def test_overlapping_boxes_count_once() -> None:
    boxes = [_box(0, 0, 50, 50), _box(25, 25, 75, 75)]

    assert covered_pct(boxes, WHOLE) == 43.8  # 2500 + 2500 - 625 of 10000


def test_only_the_part_inside_the_zone_counts() -> None:
    right_half = NormalizedBox(0.5, 0, 1, 1)

    assert covered_pct([_box(0, 0, 60, 100)], right_half) == 20.0
    assert covered_pct([_box(0, 0, 40, 100)], right_half) == 0.0


def test_no_boxes_cover_nothing() -> None:
    assert covered_pct([], WHOLE) == 0.0


def test_the_mock_returns_its_boxes_and_records_calls() -> None:
    mock = MockSegmentation([_box(0, 0, 10, 10)])

    assert mock.segment(b"png", "brown patch") == (_box(0, 0, 10, 10),)
    assert mock.calls == [(b"png", "brown patch")]
