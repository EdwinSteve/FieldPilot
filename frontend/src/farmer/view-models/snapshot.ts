// One read of the farm, and the facts several screens share.
import type {
  Clock,
  Cycle,
  EmergencyStop,
  Imagery,
  LogEvent,
  Notification,
  Plot,
  Reading,
  Report,
  Task,
  Zone,
} from "../../types/api";
import { en } from "../i18n/en";
import { zoneLabel } from "../lib/names";
import { roundReading, soilIsDry, soilStatus } from "../lib/soilStatus";
import type { SoilReading, SoilTone } from "./types";

export interface FarmSnapshot {
  chatLive: boolean;
  plot: Plot;
  clock: Clock;
  /** The demo farm has one zone; the screens follow the first. */
  zone: Zone | null;
  /** Soil moisture, oldest first. */
  readings: Reading[];
  cycle: Cycle | null;
  tasks: Task[];
  notifications: Notification[];
  reports: Report[];
  stop: EmergencyStop;
  imagery: Imagery;
  verdicts: LogEvent[];
  executions: LogEvent[];
  failures: LogEvent[];
  rejections: LogEvent[];
  refusals: LogEvent[];
  notices: LogEvent[];
}

export function zoneName(snapshot: FarmSnapshot): string {
  return snapshot.zone === null ? en.names.yourField : zoneLabel(snapshot.zone.name);
}

export function fieldCapacity(snapshot: FarmSnapshot): number {
  return snapshot.zone?.field_capacity_pct ?? 0;
}

export function latestReading(snapshot: FarmSnapshot, atIso?: string): Reading | null {
  const limit = Date.parse(atIso ?? snapshot.clock.now);
  const past = snapshot.readings.filter((reading) => Date.parse(reading.recorded_at) <= limit);
  return past.at(-1) ?? null;
}

export function soilAt(snapshot: FarmSnapshot, atIso?: string): SoilReading | null {
  const reading = latestReading(snapshot, atIso);
  if (reading === null) return null;
  return { value: roundReading(reading.value), fieldCapacity: fieldCapacity(snapshot) };
}

export function soilTone(soil: SoilReading): SoilTone {
  return soilIsDry(soilStatus(soil.value, soil.fieldCapacity)) ? "needs" : "good";
}

export function soilStatusLabel(soil: SoilReading): string {
  return en.soil.status[soilStatus(soil.value, soil.fieldCapacity)];
}

export function soilTileLabel(soil: SoilReading): string {
  return en.soil.tiles[soilStatus(soil.value, soil.fieldCapacity)];
}

export function volumeOf(task: Task): number | null {
  const volume = task.params.volume_mm;
  return typeof volume === "number" ? roundReading(volume) : null;
}

export function isWatering(task: Task): boolean {
  return task.action_type === "irrigation" || task.action_type === "extra_irrigation";
}

export function pendingTasks(snapshot: FarmSnapshot): Task[] {
  return snapshot.tasks.filter((task) => task.status === "pending_approval");
}

export function eventOfTask(events: readonly LogEvent[], taskId: number): LogEvent | null {
  return events.find((event) => event.task_id === taskId) ?? null;
}

export function questionOf(task: Task, zone: string): string {
  if (task.action_type === "irrigation") return en.task.water(zone);
  if (task.action_type === "extra_irrigation") return en.task.extraWater(zone);
  return en.task.other;
}

export function plotOffset(snapshot: FarmSnapshot): number {
  return snapshot.plot.utc_offset_hours;
}
