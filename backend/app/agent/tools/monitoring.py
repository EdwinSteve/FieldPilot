"""submit_assessment: Monitoring's closing tool, with its checks inside (§4.8, D050)."""

from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.agent.brief import Assessment, BriefDraft, ObservationKind, ZoneAssessment
from app.agent.citations import cited_facts, unsupported_numbers, value_matches
from app.agent.tools.field_tools import ReadContext
from app.agent.tools.registry import Tool, ToolRefusedError
from app.domain.models import JsonObject


class ZoneInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zone_id: int
    status: Literal["dry", "ok", "wet"]
    moisture_pct: float | None = Field(
        description="The soil moisture you read for this zone, or null if it had no reading."
    )
    cited: list[str] = Field(min_length=1, description="observation_ids this zone relies on")


class AssessmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zones: list[ZoneInput] = Field(min_length=1)
    summary: str = Field(min_length=1)


def monitoring_tools(read: ReadContext, draft: BriefDraft) -> list[Tool[Any]]:
    return [
        Tool(
            "submit_assessment",
            "Submit the assessment of every zone of the plot. Closes the task. Each zone must "
            "cite observation_ids from your reads; numbers must match what you read.",
            AssessmentInput,
            _submit(read, draft),
            closes_run=True,
        )
    ]


def _submit(read: ReadContext, draft: BriefDraft) -> Callable[[AssessmentInput], JsonObject]:
    def handler(args: AssessmentInput) -> JsonObject:
        problems = _problems(read, args)
        if problems:
            raise ToolRefusedError("Assessment refused: " + " ".join(problems))
        draft.assessment = Assessment(
            tuple(
                ZoneAssessment(z.zone_id, z.status, z.moisture_pct, tuple(z.cited))
                for z in args.zones
            ),
            args.summary,
        )
        return {"accepted": True, "zones": len(args.zones)}

    return handler


def _problems(read: ReadContext, args: AssessmentInput) -> list[str]:
    expected = {zone.zone_id for zone in read.reader.zones(read.plot_id)}
    given = [zone.zone_id for zone in args.zones]
    problems = []
    if sorted(given) != sorted(expected):
        missing = sorted(expected - set(given))
        repeated = sorted({z for z in given if given.count(z) > 1})
        unknown = sorted(set(given) - expected)
        problems.append(
            f"Every zone of the plot exactly once (missing {missing}, repeated {repeated}, "
            f"not in the plot {unknown})."
        )
    for zone in args.zones:
        problems += _zone_problems(read, zone)
    all_cited = [oid for zone in args.zones for oid in zone.cited]
    facts, _ = cited_facts(read.ledger, all_cited)
    unsupported = unsupported_numbers(args.summary, facts)
    if unsupported:
        problems.append(f"Summary numbers not in any cited observation: {unsupported}.")
    return problems


def _zone_problems(read: ReadContext, zone: ZoneInput) -> list[str]:
    _, missing = cited_facts(read.ledger, zone.cited)
    if missing:
        return [f"Zone {zone.zone_id}: cited ids you never read: {missing}."]
    foreign = [
        oid
        for oid in zone.cited
        if (o := read.ledger.get(oid)) is not None and o.zone_id not in (None, zone.zone_id)
    ]
    if foreign:
        return [f"Zone {zone.zone_id}: cited observations of another zone: {foreign}."]
    if zone.moisture_pct is None:
        return []
    readings = [
        o
        for oid in zone.cited
        if (o := read.ledger.get(oid)) is not None and o.kind is ObservationKind.SOIL_MOISTURE
    ]
    if not readings:
        return [f"Zone {zone.zone_id}: moisture_pct needs a cited soil moisture reading."]
    if not any(
        isinstance(o.value, float | int) and value_matches(float(o.value), zone.moisture_pct)
        for o in readings
    ):
        return [
            f"Zone {zone.zone_id}: moisture_pct {zone.moisture_pct} matches no cited reading "
            f"({[o.value for o in readings]})."
        ]
    return []
