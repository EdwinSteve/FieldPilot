"""Read-only tools over the field. Every value returned is recorded in the ledger (D050)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.agent.brief import Observation, ObservationKind, ObservationLedger
from app.agent.field import FieldReader, IrrigationRecord, ZoneView
from app.agent.tools.registry import Tool, ToolRefusedError
from app.domain.models import JsonObject, JsonValue


@dataclass(frozen=True)
class ReadContext:
    """What the read tools of one run share: the plot, the port, the ledger, the clock."""

    plot_id: int
    reader: FieldReader
    ledger: ObservationLedger
    now: Callable[[], datetime]  # simulated time (principle 7)


class NoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ZoneArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zone_id: int


def read_tools(ctx: ReadContext) -> list[Tool[Any]]:
    return [
        Tool("list_zones", "List the zones of the plot with their ids.", NoArgs, _list_zones(ctx)),
        Tool(
            "read_zone",
            "Latest soil moisture, field capacity, last irrigation and upcoming irrigations "
            "of one zone. Each value has an observation_id to cite.",
            ZoneArgs,
            _read_zone(ctx),
        ),
        Tool(
            "read_forecast",
            "Rain expected in the next 24 h for the plot, in mm. null means unknown.",
            NoArgs,
            _read_forecast(ctx),
        ),
        Tool(
            "read_crop_stage",
            "Current crop stage, accumulated growing degree-days and crop coefficient (Kc).",
            NoArgs,
            _read_crop_stage(ctx),
        ),
    ]


def cite(observation: Observation) -> dict[str, JsonValue]:
    """How an observation is shown to the model."""
    return {
        "observation_id": observation.id,
        "value": observation.value,
        "unit": observation.unit,
        "at": observation.at.isoformat() if observation.at else None,
    }


def _list_zones(ctx: ReadContext) -> Callable[[NoArgs], JsonObject]:
    def handler(_: NoArgs) -> JsonObject:
        zones = ctx.reader.zones(ctx.plot_id)
        return {"zones": [{"zone_id": z.zone_id, "name": z.name} for z in zones]}

    return handler


def _read_zone(ctx: ReadContext) -> Callable[[ZoneArgs], JsonObject]:
    def handler(args: ZoneArgs) -> JsonObject:
        zone = ctx.reader.zone(ctx.plot_id, args.zone_id)
        if zone is None:
            raise ToolRefusedError(
                f"Zone {args.zone_id} is not in this plot. Call list_zones for the valid ids."
            )
        return _zone_result(ctx.ledger, zone)

    return handler


def _zone_result(ledger: ObservationLedger, zone: ZoneView) -> JsonObject:
    moisture = None
    if zone.moisture is not None:
        moisture = cite(
            ledger.add(
                Observation(
                    f"reading-{zone.moisture.reading_id}",
                    ObservationKind.SOIL_MOISTURE,
                    zone.zone_id,
                    zone.moisture.value_pct,
                    "%",
                    zone.moisture.recorded_at,
                )
            )
        )
    capacity = ledger.add(
        Observation(
            f"zone-{zone.zone_id}-field-capacity",
            ObservationKind.FIELD_CAPACITY,
            zone.zone_id,
            zone.field_capacity_pct,
            "%",
            None,
        )
    )
    last = zone.last_irrigation
    return {
        "zone_id": zone.zone_id,
        "name": zone.name,
        "soil_moisture": moisture,
        "field_capacity": cite(capacity),
        "last_irrigation": None if last is None else _irrigation(ledger, zone.zone_id, last),
        "upcoming": [_irrigation(ledger, zone.zone_id, task) for task in zone.upcoming],
    }


def _irrigation(
    ledger: ObservationLedger, zone_id: int, task: IrrigationRecord
) -> dict[str, JsonValue]:
    observation = ledger.add(
        Observation(
            f"task-{task.task_id}",
            ObservationKind.IRRIGATION,
            zone_id,
            task.volume_mm,
            "mm",
            task.scheduled_for,
        )
    )
    return {
        **cite(observation),
        "task_id": task.task_id,
        "action_type": task.action_type,
        "status": task.status,
    }


def _read_forecast(ctx: ReadContext) -> Callable[[NoArgs], JsonObject]:
    def handler(_: NoArgs) -> JsonObject:
        at = ctx.now()
        rain = ctx.reader.rain_mm_next_24h(ctx.plot_id, at)
        observation = ctx.ledger.add(
            Observation(
                f"forecast-plot-{ctx.plot_id}-{at:%Y-%m-%dT%H:%MZ}",
                ObservationKind.RAIN_FORECAST,
                None,
                rain,
                "mm",
                at,
            )
        )
        note = (
            "Unknown forecast: the gate holds any irrigation for approval."
            if rain is None
            else None
        )
        return {"rain_next_24h": cite(observation), "note": note}

    return handler


def _read_crop_stage(ctx: ReadContext) -> Callable[[NoArgs], JsonObject]:
    def handler(_: NoArgs) -> JsonObject:
        stage = ctx.reader.crop_stage(ctx.plot_id)
        cycle = stage.cycle_id
        facts = [
            Observation(f"stage-cycle-{cycle}", ObservationKind.STAGE, None, stage.stage, "", None),
            Observation(
                f"gdd-cycle-{cycle}", ObservationKind.GDD, None, stage.accumulated_gdd, "GDD", None
            ),
            Observation(f"kc-cycle-{cycle}", ObservationKind.KC, None, stage.kc, "", None),
        ]
        stage_obs, gdd, kc = (ctx.ledger.add(fact) for fact in facts)
        return {
            "stage": {**cite(stage_obs), "display_es": stage.stage_display_es},
            "accumulated_gdd": cite(gdd),
            "kc": cite(kc),
        }

    return handler
