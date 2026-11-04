"""The simulated sensor kit of a demo plot (D089): zones, sensors and a first reading.

The simulator takes over a zone once it has a soil-moisture reading
(`ensure_simulated`), so after this the ticker records every sensor, as it
does for the seed farm. Outside the demo nothing installs a kit.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.domain.enums import SensorKind
from app.domain.errors import ConfigError
from app.domain.models import Plot, Reading, Sensor, Zone
from app.persistence.ports import UnitOfWork

UNITS = {SensorKind.SOIL_MOISTURE: "%", SensorKind.TEMPERATURE: "°C", SensorKind.HUMIDITY: "%"}


class FieldInstaller(Protocol):
    """Gives a new plot its zones and sensors, inside the plot's own transaction."""

    def install(self, uow: UnitOfWork, plot: Plot, at: datetime) -> Sequence[Zone]: ...


@dataclass(frozen=True)
class KitZone:
    area_share: float
    field_capacity_pct: float
    soil_moisture_pct: float


@dataclass(frozen=True)
class SensorKit:
    zones: tuple[KitZone, ...]
    sensors: tuple[SensorKind, ...]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _Zone(_Strict):
    area_share: float = Field(gt=0, le=1)
    field_capacity_pct: float = Field(gt=0, le=100)
    soil_moisture_pct: float = Field(ge=0, le=100)


class _KitFile(_Strict):
    zones: list[_Zone] = Field(min_length=1)
    sensors: list[SensorKind] = Field(min_length=1)

    @model_validator(mode="after")
    def _whole(self) -> "_KitFile":
        if abs(sum(z.area_share for z in self.zones) - 1) > 1e-6:
            raise ValueError("the zones' area_share must add up to 1")
        if SensorKind.SOIL_MOISTURE not in self.sensors:
            raise ValueError("the simulator needs a soil_moisture sensor to start a zone")
        if len(set(self.sensors)) != len(self.sensors):
            raise ValueError("each sensor kind once")
        return self


def load_sensor_kit(path: Path) -> SensorKit:
    try:
        parsed = _KitFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise ConfigError(f"{path.name}: {error}") from error
    zones = tuple(KitZone(**z.model_dump()) for z in parsed.zones)
    return SensorKit(zones, tuple(parsed.sensors))


class SensorKitInstaller:
    """Installs the kit: zone n is named by `zone_name(n)`, with its own valve."""

    def __init__(self, kit: SensorKit, zone_name: Callable[[int], str]) -> None:
        self._kit = kit
        self._zone_name = zone_name

    def install(self, uow: UnitOfWork, plot: Plot, at: datetime) -> Sequence[Zone]:
        plot_id = _stored(plot.id)
        zones = []
        for number, spec in enumerate(self._kit.zones, start=1):
            zone = uow.zones.add(
                Zone(plot_id, self._zone_name(number), round(plot.area_ha * spec.area_share, 4),
                     spec.field_capacity_pct, valve_id=f"p{plot_id}-v{number}")
            )  # fmt: skip
            for kind in self._kit.sensors:
                sensor = uow.sensors.add(Sensor(_stored(zone.id), kind, UNITS[kind]))
                if kind is SensorKind.SOIL_MOISTURE:
                    uow.readings.add_many([Reading(_stored(sensor.id), spec.soil_moisture_pct, at)])
            zones.append(zone)
        return zones


def _stored(entity_id: int | None) -> int:
    if entity_id is None:
        raise ValueError("entity was not stored")
    return entity_id
