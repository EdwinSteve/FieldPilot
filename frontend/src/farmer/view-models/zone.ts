import { en } from "../i18n/en";
import { formatClock, plusDays, shortWeekday } from "../lib/farmTime";
import { activeRun } from "../lib/irrigationRun";
import { cropLabel } from "../lib/names";
import { sensorIsStale } from "../lib/sensorHealth";
import { pointsToFull, roundReading } from "../lib/soilStatus";
import { percentFull, soilTrend } from "../lib/soilTrend";
import {
  fieldCapacity,
  latestReading,
  plotOffset,
  soilAt,
  soilLevelOf,
  soilStatusLabel,
  zoneName,
  type FarmSnapshot,
} from "./snapshot";
import type { Level } from "../lib/statusLevel";
import type { ZoneView } from "./types";

const HISTORY_DAYS = 7;

function history(snapshot: FarmSnapshot) {
  const now = snapshot.clock.now;
  const start = Date.parse(plusDays(now, -HISTORY_DAYS));
  const end = Date.parse(now);
  return snapshot.readings.filter((reading) => {
    const at = Date.parse(reading.recorded_at);
    return at >= start && at <= end;
  });
}

function sensorLevel(snapshot: FarmSnapshot): Level {
  const reading = latestReading(snapshot);
  if (reading === null) return "neutral";
  return sensorIsStale(reading.recorded_at, snapshot.clock.now) ? "bad" : "good";
}

function sensorText(snapshot: FarmSnapshot): string {
  const reading = latestReading(snapshot);
  if (reading === null) return en.zone.sensorNone;
  if (sensorIsStale(reading.recorded_at, snapshot.clock.now)) return en.zone.sensorStale;
  return en.zone.sensorOk(formatClock(reading.recorded_at, plotOffset(snapshot)));
}

export function zoneView(snapshot: FarmSnapshot, zoneId: number): ZoneView | null {
  const zone = snapshot.zone;
  if (zone === null || zone.id !== zoneId) return null;
  const name = zoneName(snapshot);
  const capacity = fieldCapacity(snapshot);
  const soil = soilAt(snapshot);
  const points = history(snapshot);
  const values = points.map((reading) => roundReading(reading.value));
  const running = activeRun(snapshot.executions, snapshot.tasks, snapshot.clock.now);
  const offset = plotOffset(snapshot);
  const missing = soil === null ? 0 : pointsToFull(soil.value, capacity);
  const level: Level = soil === null ? "neutral" : soilLevelOf(soil);
  const trend = soilTrend(snapshot.readings, snapshot.clock.now);
  return {
    name,
    caption: en.zone.caption(
      zone.area_ha,
      snapshot.cycle === null ? "" : cropLabel(snapshot.cycle.crop),
    ),
    status: soil === null ? en.soil.unknown : soilStatusLabel(soil),
    level,
    soil: { ...(soil ?? { value: 0, fieldCapacity: capacity }), level },
    display: soil === null ? en.soil.unknown : `${soil.value}%`,
    percentFull: soil === null ? null : en.soil.percentFull(percentFull(soil.value, capacity)),
    trend: trend === null ? null : en.soil.trendLine[trend.direction](roundReading(trend.previous)),
    needsMore: missing > 0 ? en.zone.needsMore(name, missing) : en.zone.isFull(name),
    history: values,
    historyStart: points[0] === undefined ? "" : shortWeekday(points[0].recorded_at, offset),
    historyAlt: en.zone.historyAlt(values[0] ?? 0, values.at(-1) ?? 0, capacity),
    valve:
      running === null
        ? en.zone.valveClosed
        : en.zone.valveOpen(formatClock(running.endsAt, offset)),
    valveLevel: running === null ? "neutral" : "info",
    sensor: sensorText(snapshot),
    sensorLevel: sensorLevel(snapshot),
  };
}
