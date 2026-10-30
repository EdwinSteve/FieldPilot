"""read_imagery and submit_imaging: the Imaging subagent's tools (D050, D060)."""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.agent.brief import (
    BriefDraft,
    ImagingResult,
    Observation,
    ObservationKind,
    ObservationLedger,
    ZoneImaging,
)
from app.agent.citations import value_matches
from app.agent.field import ImageryReader, ImageryView, ZoneImagery
from app.agent.tools.field_tools import NoArgs, ReadContext, cite
from app.agent.tools.registry import Tool, ToolRefusedError
from app.domain.models import JsonObject, JsonValue

NO_SCENE = "No satellite scene for this plot: submit_imaging with an empty zones list."


class ZoneImagingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zone_id: int
    ndvi_mean: float | None
    low_ndvi_pct: float | None
    bare_soil_pct: float | None
    low_vigor: bool = Field(description="true when ndvi_mean is below the threshold")
    cited: list[str] = Field(min_length=1)


class ImagingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zones: list[ZoneImagingInput]


def imaging_tools(read: ReadContext, draft: BriefDraft, imagery: ImageryReader) -> list[Tool[Any]]:
    return [
        Tool(
            "read_imagery",
            "NDVI and bare soil per zone from the latest satellite scene. bare_soil_pct "
            "comes from boxes and can overstate round patches.",
            NoArgs,
            _read(read, draft, imagery),
        ),
        Tool(
            "submit_imaging",
            "Submit the imaging result for every zone the scene covers. Closes the task. "
            "Values must be exactly the ones read_imagery returned.",
            ImagingInput,
            _submit(read, draft, imagery),
            closes_run=True,
        ),
    ]


def _read(
    read: ReadContext, draft: BriefDraft, imagery: ImageryReader
) -> Callable[[NoArgs], JsonObject]:
    def handler(_: NoArgs) -> JsonObject:
        view = imagery.imagery(read.plot_id, draft.day)
        if view is None:
            return {"scene": None, "note": NO_SCENE}
        zones: list[JsonValue] = [_zone_result(read.ledger, view, z) for z in view.zones]
        return {
            "scene": {
                "scene_id": view.scene_id,
                "acquired_on": view.acquired_on.isoformat(),
                "synthetic": view.synthetic,
                "low_ndvi_threshold": view.low_ndvi_threshold,
            },
            "zones": zones,
            "note": view.segmentation_note,
        }

    return handler


def _zone_result(
    ledger: ObservationLedger, view: ImageryView, zone: ZoneImagery
) -> dict[str, JsonValue]:
    facts = (
        (ObservationKind.NDVI, "ndvi", zone.ndvi_mean, ""),
        (ObservationKind.LOW_NDVI, "low-ndvi", zone.low_ndvi_pct, "%"),
        (ObservationKind.BARE_SOIL, "bare-soil", zone.bare_soil_pct, "%"),
    )
    result: dict[str, JsonValue] = {"zone_id": zone.zone_id}
    for kind, prefix, value, unit in facts:
        observation = ledger.add(
            Observation(
                f"{prefix}-{view.scene_id}-zone-{zone.zone_id}",
                kind,
                zone.zone_id,
                value,
                unit,
                None,
            )
        )
        result[kind.value] = cite(observation)
    return result


def _submit(
    read: ReadContext, draft: BriefDraft, imagery: ImageryReader
) -> Callable[[ImagingInput], JsonObject]:
    def handler(args: ImagingInput) -> JsonObject:
        view = imagery.imagery(read.plot_id, draft.day)
        problems = _problems(read.ledger, view, args)
        if problems:
            raise ToolRefusedError("Imaging refused: " + " ".join(problems))
        draft.imaging = ImagingResult(
            None if view is None else view.scene_id,
            tuple(
                ZoneImaging(
                    z.zone_id,
                    z.ndvi_mean,
                    z.low_ndvi_pct,
                    z.bare_soil_pct,
                    z.low_vigor,
                    tuple(z.cited),
                )
                for z in args.zones
            ),
        )
        return {"accepted": True, "zones": len(args.zones)}

    return handler


def _problems(ledger: ObservationLedger, view: ImageryView | None, args: ImagingInput) -> list[str]:
    truth = {} if view is None else {zone.zone_id: zone for zone in view.zones}
    given = [zone.zone_id for zone in args.zones]
    problems = []
    if sorted(given) != sorted(truth):
        problems.append(
            f"Submit every zone the scene covers exactly once: expected {sorted(truth)}, "
            f"got {given}."
        )
    for zone in args.zones:
        expected = truth.get(zone.zone_id)
        if view is not None and expected is not None:
            problems += _zone_problems(ledger, view.low_ndvi_threshold, expected, zone)
    return problems


def _zone_problems(
    ledger: ObservationLedger, threshold: float, expected: ZoneImagery, zone: ZoneImagingInput
) -> list[str]:
    problems = []
    unknown = [oid for oid in zone.cited if ledger.get(oid) is None]
    foreign = [
        oid
        for oid in zone.cited
        if (o := ledger.get(oid)) is not None and o.zone_id not in (None, zone.zone_id)
    ]
    if unknown:
        problems.append(f"Zone {zone.zone_id}: cited ids you never read: {unknown}.")
    if foreign:
        problems.append(f"Zone {zone.zone_id}: cited observations of another zone: {foreign}.")
    problems.extend(
        f"Zone {zone.zone_id}: {name} {getattr(zone, name)} is not the computed "
        f"{getattr(expected, name)}."
        for name in ("ndvi_mean", "low_ndvi_pct", "bare_soil_pct")
        if not _same(getattr(expected, name), getattr(zone, name))
    )
    low = expected.ndvi_mean is not None and expected.ndvi_mean < threshold
    if zone.low_vigor != low:
        problems.append(
            f"Zone {zone.zone_id}: low_vigor must be {str(low).lower()} "
            f"(mean NDVI {expected.ndvi_mean} vs threshold {threshold})."
        )
    return problems


def _same(computed: float | None, submitted: float | None) -> bool:
    if computed is None or submitted is None:
        return computed is submitted
    return value_matches(computed, submitted)
