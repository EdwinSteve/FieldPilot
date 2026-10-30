import json
from dataclasses import replace
from datetime import date

import pytest

from app.agent.brief import BriefDraft, ObservationKind, ObservationLedger
from app.agent.tools.field_tools import ReadContext
from app.agent.tools.imaging import NO_SCENE, imaging_tools
from app.agent.tools.registry import ToolOutcome, ToolRegistry
from tests.unit.agent.field_fakes import NOW, SCENE, FakeImagery, FakeReader

CITED_2 = ["ndvi-scene-1-zone-2", "low-ndvi-scene-1-zone-2", "bare-soil-scene-1-zone-2"]
CITED_3 = ["ndvi-scene-1-zone-3", "low-ndvi-scene-1-zone-3", "bare-soil-scene-1-zone-3"]


def _zone(zone_id: int, **overrides: object) -> dict[str, object]:
    base: dict[int, dict[str, object]] = {
        2: {
            "ndvi_mean": 0.378,
            "low_ndvi_pct": 21.2,
            "bare_soil_pct": 25.3,
            "low_vigor": True,
            "cited": CITED_2,
        },
        3: {
            "ndvi_mean": 0.802,
            "low_ndvi_pct": 0.0,
            "bare_soil_pct": 0.0,
            "low_vigor": False,
            "cited": CITED_3,
        },
    }
    return {"zone_id": zone_id, **base[zone_id], **overrides}


@pytest.fixture
def ledger() -> ObservationLedger:
    return ObservationLedger()


@pytest.fixture
def draft() -> BriefDraft:
    return BriefDraft(1, date(2026, 10, 28))


def _tools(ledger: ObservationLedger, draft: BriefDraft, imagery: FakeImagery) -> ToolRegistry:
    read = ReadContext(1, FakeReader(), ledger, lambda: NOW)
    return ToolRegistry(imaging_tools(read, draft, imagery))


@pytest.fixture
def tools(ledger: ObservationLedger, draft: BriefDraft) -> ToolRegistry:
    registry = _tools(ledger, draft, FakeImagery())
    registry.call("read_imagery", "{}")
    return registry


def _submit(tools: ToolRegistry, zones: list[dict[str, object]]) -> ToolOutcome:
    return tools.call("submit_imaging", json.dumps({"zones": zones}))


def test_read_imagery_records_three_observations_per_zone(
    ledger: ObservationLedger, draft: BriefDraft
) -> None:
    outcome = _tools(ledger, draft, FakeImagery()).call("read_imagery", "{}")

    assert outcome.result is not None
    scene = outcome.result["scene"]
    assert isinstance(scene, dict) and scene["low_ndvi_threshold"] == 0.4
    bare = ledger.get("bare-soil-scene-1-zone-2")
    assert bare is not None and (bare.kind, bare.value, bare.unit) == (
        ObservationKind.BARE_SOIL,
        25.3,
        "%",
    )
    ndvi = ledger.get("ndvi-scene-1-zone-2")
    assert ndvi is not None and (ndvi.value, ndvi.unit) == (0.378, "")
    assert len(ledger) == 6


def test_a_correct_submission_fills_the_brief(tools: ToolRegistry, draft: BriefDraft) -> None:
    outcome = _submit(tools, [_zone(2), _zone(3)])

    assert outcome.error is None and outcome.closes_run
    assert draft.imaging is not None and draft.imaging.scene_id == "scene-1"
    assert [(z.zone_id, z.low_vigor) for z in draft.imaging.zones] == [(2, True), (3, False)]


def test_no_scene_means_an_empty_result(ledger: ObservationLedger, draft: BriefDraft) -> None:
    """D060: the cycle does not stop for lack of imagery."""
    tools = _tools(ledger, draft, FakeImagery(None))

    read = tools.call("read_imagery", "{}")
    outcome = _submit(tools, [])

    assert read.result == {"scene": None, "note": NO_SCENE}
    assert outcome.closes_run
    assert (
        draft.imaging is not None and draft.imaging.scene_id is None and draft.imaging.zones == ()
    )


def test_zones_without_a_scene_are_refused(ledger: ObservationLedger, draft: BriefDraft) -> None:
    tools = _tools(ledger, draft, FakeImagery(None))

    outcome = _submit(tools, [_zone(2)])

    assert outcome.error is not None and "expected [], got [2]" in outcome.error


@pytest.mark.parametrize(
    ("zones", "message"),
    [
        ([_zone(2)], "expected [2, 3], got [2]"),
        ([_zone(2), _zone(3), _zone(3)], "got [2, 3, 3]"),
        ([_zone(2, ndvi_mean=0.45), _zone(3)], "ndvi_mean 0.45 is not the computed 0.378"),
        ([_zone(2, bare_soil_pct=10.0), _zone(3)], "bare_soil_pct 10.0 is not the computed 25.3"),
        ([_zone(2, low_ndvi_pct=None), _zone(3)], "low_ndvi_pct None is not the computed 21.2"),
        ([_zone(2, low_vigor=False), _zone(3)], "low_vigor must be true"),
        ([_zone(2, cited=["ndvi-x"]), _zone(3)], "cited ids you never read: ['ndvi-x']"),
        ([_zone(2, cited=CITED_3), _zone(3)], "cited observations of another zone"),
    ],
)
def test_a_wrong_submission_is_refused(
    tools: ToolRegistry, draft: BriefDraft, zones: list[dict[str, object]], message: str
) -> None:
    outcome = _submit(tools, zones)

    assert outcome.error is not None and message in outcome.error
    assert draft.imaging is None


def test_an_unknown_bare_soil_must_stay_unknown(
    ledger: ObservationLedger, draft: BriefDraft
) -> None:
    zones = tuple(replace(z, bare_soil_pct=None) for z in SCENE.zones)
    tools = _tools(
        ledger, draft, FakeImagery(replace(SCENE, zones=zones, segmentation_note="down"))
    )
    tools.call("read_imagery", "{}")

    filled = _submit(tools, [_zone(2), _zone(3, bare_soil_pct=None)])
    kept = _submit(tools, [_zone(2, bare_soil_pct=None), _zone(3, bare_soil_pct=None)])

    assert (
        filled.error is not None and "bare_soil_pct 25.3 is not the computed None" in filled.error
    )
    assert kept.closes_run


def test_a_mean_exactly_at_the_threshold_is_not_low_vigor(
    ledger: ObservationLedger, draft: BriefDraft
) -> None:
    at_threshold = (replace(SCENE.zones[0], ndvi_mean=0.4), SCENE.zones[1])
    tools = _tools(ledger, draft, FakeImagery(replace(SCENE, zones=at_threshold)))
    tools.call("read_imagery", "{}")

    low = _submit(tools, [_zone(2, ndvi_mean=0.4, low_vigor=True), _zone(3)])
    not_low = _submit(tools, [_zone(2, ndvi_mean=0.4, low_vigor=False), _zone(3)])

    assert low.error is not None and "low_vigor must be false" in low.error
    assert not_low.closes_run
