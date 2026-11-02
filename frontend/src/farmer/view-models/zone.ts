import { en } from "../i18n/en";
import { formatClock, plusDays, shortWeekday } from "../lib/farmTime";
import { activeRun } from "../lib/irrigationRun";
import { cropLabel } from "../lib/names";
import { sensorIsStale } from "../lib/sensorHealth";
import { pointsToFull, roundReading } from "../lib/soilStatus";
import {
  fieldCapacity,
  latestReading,
  plotOffset,
  soilAt,
  soilStatusLabel,
  soilTone,
  zoneName,
  type FarmSnapshot,
} from "./snapshot";
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
  return {
    name,
    caption: en.zone.caption(
      zone.area_ha,
      snapshot.cycle === null ? "" : cropLabel(snapshot.cycle.crop),
    ),
    status: soil === null ? en.soil.unknown : soilStatusLabel(soil),
    tone: soil === null ? "good" : soilTone(soil),
    soil: soil ?? { value: 0, fieldCapacity: capacity },
    display: soil === null ? en.soil.unknown : `${soil.value}%`,
    needsMore: missing > 0 ? en.zone.needsMore(name, missing) : en.zone.isFull(name),
    history: values,
    historyStart: points[0] === undefined ? "" : shortWeekday(points[0].recorded_at, offset),
    historyAlt: en.zone.historyAlt(values[0] ?? 0, values.at(-1) ?? 0, capacity),
    valve:
      running === null
        ? en.zone.valveClosed
        : en.zone.valveOpen(formatClock(running.endsAt, offset)),
    sensor: sensorText(snapshot),
  };
}
