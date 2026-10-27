"""Repositories for the physical field: plots, zones, sensors and readings."""

from collections.abc import Sequence
from datetime import datetime

from sqlmodel import Session, col, select

from app.domain.models import Plot, Reading, Sensor, Zone
from app.persistence import mappers
from app.persistence.repositories._base import get_row_or_raise, insert
from app.persistence.tables import PlotRow, ReadingRow, SensorRow, ZoneRow


class SqlPlotRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, plot: Plot) -> Plot:
        return mappers.plot_from_row(insert(self._session, mappers.plot_to_row(plot)))

    def get(self, plot_id: int) -> Plot:
        return mappers.plot_from_row(get_row_or_raise(self._session, PlotRow, plot_id, "Plot"))

    def list(self) -> Sequence[Plot]:
        rows = self._session.exec(select(PlotRow).order_by(col(PlotRow.id)))
        return [mappers.plot_from_row(row) for row in rows]


class SqlZoneRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, zone: Zone) -> Zone:
        return mappers.zone_from_row(insert(self._session, mappers.zone_to_row(zone)))

    def get(self, zone_id: int) -> Zone:
        return mappers.zone_from_row(get_row_or_raise(self._session, ZoneRow, zone_id, "Zone"))

    def list_by_plot(self, plot_id: int) -> Sequence[Zone]:
        query = select(ZoneRow).where(ZoneRow.plot_id == plot_id).order_by(col(ZoneRow.id))
        return [mappers.zone_from_row(row) for row in self._session.exec(query)]


class SqlSensorRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, sensor: Sensor) -> Sensor:
        return mappers.sensor_from_row(insert(self._session, mappers.sensor_to_row(sensor)))

    def list_by_zone(self, zone_id: int) -> Sequence[Sensor]:
        query = select(SensorRow).where(SensorRow.zone_id == zone_id).order_by(col(SensorRow.id))
        return [mappers.sensor_from_row(row) for row in self._session.exec(query)]


class SqlReadingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_many(self, readings: Sequence[Reading]) -> Sequence[Reading]:
        rows = [mappers.reading_to_row(reading) for reading in readings]
        self._session.add_all(rows)
        self._session.flush()
        return [mappers.reading_from_row(row) for row in rows]

    def latest(self, sensor_id: int) -> Reading | None:
        query = (
            select(ReadingRow)
            .where(ReadingRow.sensor_id == sensor_id)
            .order_by(col(ReadingRow.recorded_at).desc(), col(ReadingRow.id).desc())
            .limit(1)
        )
        row = self._session.exec(query).first()
        return mappers.reading_from_row(row) if row else None

    def list_for_sensor(
        self, sensor_id: int, since: datetime | None = None, until: datetime | None = None
    ) -> Sequence[Reading]:
        query = select(ReadingRow).where(ReadingRow.sensor_id == sensor_id)
        if since is not None:
            query = query.where(col(ReadingRow.recorded_at) >= since)
        if until is not None:
            query = query.where(col(ReadingRow.recorded_at) < until)
        query = query.order_by(col(ReadingRow.recorded_at), col(ReadingRow.id))
        return [mappers.reading_from_row(row) for row in self._session.exec(query)]
