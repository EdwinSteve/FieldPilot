"""The two specialists of D093: crop_health and soil_nutrition, read-only.

Their read tools record every value in the ledger, as the field tools do;
their closing tools check that each zone appears once and cites what was read.
"""

from collections.abc import Callable, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.agent.brief import (
    BriefDraft,
    Observation,
    ObservationKind,
    ObservationLedger,
    ZoneHealth,
    ZoneNutrition,
)
from app.agent.citations import cited_facts, unsupported_numbers
from app.agent.field import Agronomy, Microclimate, SoilView
from app.agent.tools.field_tools import NoArgs, ReadContext, ZoneArgs, cite
from app.agent.tools.registry import Tool, ToolRefusedError
from app.domain.models import JsonObject, JsonValue

UNAVAILABLE = "This farm has no agronomy data source configured."
THREATS = Literal["fungal_disease", "pests", "water_stress", "low_vigor", "bare_soil"]
DEFICITS = Literal["nitrogen", "phosphorus", "potassium", "ph_low", "ph_high"]


class HealthZoneInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zone_id: int
    risk: Literal["low", "moderate", "high"]
    threats: list[THREATS] = Field(description="What puts the crop at risk; empty when none.")
    note: str = Field(min_length=1, description="One sentence: what you saw and why.")
    cited: list[str] = Field(min_length=1, description="observation_ids this zone relies on")


class HealthInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zones: list[HealthZoneInput] = Field(min_length=1)


class NutritionZoneInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zone_id: int
    status: Literal["ok", "low", "high"]
    deficits: list[DEFICITS] = Field(description="Values outside the crop's target; empty if ok.")
    note: str = Field(min_length=1, description="One sentence: what you read and why.")
    cited: list[str] = Field(min_length=1, description="observation_ids this zone relies on")


class NutritionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zones: list[NutritionZoneInput] = Field(min_length=1)


def agronomy_tools(
    read: ReadContext, draft: BriefDraft, agronomy: Agronomy | None
) -> list[Tool[Any]]:
    return [
        Tool(
            "read_microclimate",
            "Air temperature and relative humidity of one zone over the last 48 h, and the "
            "hours of humid leaves (RH >= 90 % between 10 and 30 °C), when fungal diseases "
            "spread. Each value has an observation_id to cite.",
            ZoneArgs,
            _read_microclimate(read, agronomy),
        ),
        Tool(
            "read_soil",
            "Soil pH, organic carbon and available nitrogen, phosphorus and potassium of one "
            "zone, each with the crop's target range. Each value has an observation_id.",
            ZoneArgs,
            _read_soil(read, agronomy),
        ),
        Tool(
            "read_tasks",
            "The plot's open tasks (awaiting approval or scheduled), every kind, with who "
            "proposed each. Read it before proposing, replacing or cancelling a task.",
            NoArgs,
            _read_tasks(read, agronomy),
        ),
        Tool(
            "submit_health",
            "Submit the crop health of every zone. Closes the task. Each zone cites the "
            "observations behind its risk.",
            HealthInput,
            _submit_health(read, draft),
            closes_run=True,
        ),
        Tool(
            "submit_nutrition",
            "Submit the soil nutrition of every zone. Closes the task. Each zone cites the "
            "soil values behind its status.",
            NutritionInput,
            _submit_nutrition(read, draft),
            closes_run=True,
        ),
    ]


def _require(agronomy: Agronomy | None) -> Agronomy:
    if agronomy is None:
        raise ToolRefusedError(UNAVAILABLE)
    return agronomy


def _zone_or_refuse(read: ReadContext, zone_id: int) -> None:
    if read.reader.zone(read.plot_id, zone_id) is None:
        raise ToolRefusedError(f"Zone {zone_id} is not in this plot. Call list_zones.")


def _read_microclimate(
    read: ReadContext, agronomy: Agronomy | None
) -> Callable[[ZoneArgs], JsonObject]:
    def handler(args: ZoneArgs) -> JsonObject:
        source = _require(agronomy)
        _zone_or_refuse(read, args.zone_id)
        air = source.microclimate(read.plot_id, args.zone_id, read.now())
        if air is None or air.readings == 0:
            return {"zone_id": args.zone_id, "microclimate": None,
                    "note": "This zone has no temperature or humidity readings."}  # fmt: skip
        return {"zone_id": args.zone_id, **_microclimate(read.ledger, air)}

    return handler


def _microclimate(ledger: ObservationLedger, air: Microclimate) -> JsonObject:
    stamp = f"z{air.zone_id}-{air.until:%Y%m%dT%H%M}"
    values: Sequence[tuple[str, ObservationKind, float | None, str]] = (
        ("temperature_mean", ObservationKind.TEMPERATURE, air.temperature_mean_c, "°C"),
        ("temperature_max", ObservationKind.TEMPERATURE, air.temperature_max_c, "°C"),
        ("humidity_mean", ObservationKind.HUMIDITY, air.humidity_mean_pct, "%"),
        ("humidity_max", ObservationKind.HUMIDITY, air.humidity_max_pct, "%"),
        ("humid_leaf_hours", ObservationKind.HUMID_HOURS, air.humid_leaf_hours, "h"),
    )
    result: dict[str, JsonValue] = {"window_hours": air.window_hours, "readings": air.readings}
    for name, kind, value, unit in values:
        observation = Observation(
            f"air-{name.replace('_', '-')}-{stamp}",
            kind,
            air.zone_id,
            None if value is None else round(value, 1),
            unit,
            air.until,
        )
        result[name] = cite(ledger.add(observation))
    return result


def _read_soil(read: ReadContext, agronomy: Agronomy | None) -> Callable[[ZoneArgs], JsonObject]:
    def handler(args: ZoneArgs) -> JsonObject:
        source = _require(agronomy)
        _zone_or_refuse(read, args.zone_id)
        soil = source.soil(read.plot_id, args.zone_id, read.now())
        if soil is None:
            return {"zone_id": args.zone_id, "soil": None,
                    "note": "This zone has no soil data."}  # fmt: skip
        return {"zone_id": args.zone_id, **_soil(read, soil)}

    return handler


def _soil(read: ReadContext, soil: SoilView) -> JsonObject:
    day = f"{read.now():%Y%m%d}"
    values: Sequence[tuple[str, ObservationKind, float | None, str]] = (
        ("ph", ObservationKind.SOIL_PH, soil.ph, ""),
        ("organic_carbon", ObservationKind.ORGANIC_CARBON, soil.organic_carbon_g_kg, "g/kg"),
        ("nitrogen", ObservationKind.NITROGEN, soil.nitrogen_ppm, "ppm"),
        ("phosphorus", ObservationKind.PHOSPHORUS, soil.phosphorus_ppm, "ppm"),
        ("potassium", ObservationKind.POTASSIUM, soil.potassium_ppm, "ppm"),
    )
    result: dict[str, JsonValue] = {
        "ph_source": soil.ph_source,
        "simulated_probe": soil.simulated,
    }
    for name, kind, value, unit in values:
        observation = Observation(
            f"soil-{name.replace('_', '-')}-z{soil.zone_id}-{day}",
            kind,
            soil.zone_id,
            None if value is None else round(value, 1),
            unit,
            None,
        )
        shown: dict[str, JsonValue] = dict(cite(read.ledger.add(observation)))
        target = soil.targets.get(name)
        if target is not None:
            shown["target"] = {"low": target.low, "high": target.high}
        result[name] = shown
    return result


def _read_tasks(read: ReadContext, agronomy: Agronomy | None) -> Callable[[NoArgs], JsonObject]:
    def handler(_: NoArgs) -> JsonObject:
        tasks = _require(agronomy).open_tasks(read.plot_id)
        shown: list[JsonValue] = []
        for task in tasks:
            observation = read.ledger.add(
                Observation(
                    f"open-task-{task.task_id}",
                    ObservationKind.TASK,
                    task.zone_id,
                    task.action_type,
                    "",
                    task.scheduled_for,
                )
            )
            shown.append({
                "observation_id": observation.id,
                "task_id": task.task_id,
                "action_type": task.action_type,
                "zone_id": task.zone_id,
                "scheduled_for": task.scheduled_for.isoformat(),
                "status": task.status,
                "proposed_by": task.proposed_by,
                "params": dict(task.params),
                "rationale": task.rationale,
            })  # fmt: skip
        return {"tasks": shown}

    return handler


def _zone_problems(read: ReadContext, zone_ids: list[int], cited: list[list[str]]) -> list[str]:
    expected = {zone.zone_id for zone in read.reader.zones(read.plot_id)}
    problems = []
    if sorted(zone_ids) != sorted(expected):
        problems.append(f"Every zone of the plot exactly once: {sorted(expected)}.")
    for zone_id, ids in zip(zone_ids, cited, strict=True):
        _, missing = cited_facts(read.ledger, ids)
        if missing:
            problems.append(f"Zone {zone_id}: cited ids you never read: {missing}.")
    return problems


def _note_problems(read: ReadContext, notes: list[tuple[str, list[str]]]) -> list[str]:
    problems = []
    for note, ids in notes:
        facts, _ = cited_facts(read.ledger, ids)
        unsupported = unsupported_numbers(note, facts)
        if unsupported:
            problems.append(f"Numbers not in any cited observation: {unsupported}.")
    return problems


def _submit_health(read: ReadContext, draft: BriefDraft) -> Callable[[HealthInput], JsonObject]:
    def handler(args: HealthInput) -> JsonObject:
        problems = _zone_problems(
            read, [z.zone_id for z in args.zones], [z.cited for z in args.zones]
        ) + _note_problems(read, [(z.note, z.cited) for z in args.zones])
        if problems:
            raise ToolRefusedError("Health refused: " + " ".join(problems))
        draft.health = tuple(
            ZoneHealth(z.zone_id, z.risk, tuple(z.threats), z.note, tuple(z.cited))
            for z in args.zones
        )
        at_risk = [z.zone_id for z in args.zones if z.risk != "low"]
        return {"accepted": True, "zones_at_risk": list(at_risk)}

    return handler


def _submit_nutrition(
    read: ReadContext, draft: BriefDraft
) -> Callable[[NutritionInput], JsonObject]:
    def handler(args: NutritionInput) -> JsonObject:
        problems = _zone_problems(
            read, [z.zone_id for z in args.zones], [z.cited for z in args.zones]
        ) + _note_problems(read, [(z.note, z.cited) for z in args.zones])
        if problems:
            raise ToolRefusedError("Nutrition refused: " + " ".join(problems))
        draft.nutrition = tuple(
            ZoneNutrition(z.zone_id, z.status, tuple(z.deficits), z.note, tuple(z.cited))
            for z in args.zones
        )
        short = [z.zone_id for z in args.zones if z.deficits]
        return {"accepted": True, "zones_with_deficits": list(short)}

    return handler
