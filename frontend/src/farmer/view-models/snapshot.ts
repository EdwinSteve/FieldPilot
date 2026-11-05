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
  Weather,
  Zone,
} from "../../types/api";
import type { HealthResponse } from "../../types/health";
import { forecastOfDay } from "../lib/forecast";
import { plotDay } from "../../lib/format";
import type { PlanAtSowing } from "../api/lifecycle";
import { en } from "../i18n/en";
import { zoneLabel } from "../lib/names";
import type { ZoneSoil } from "../lib/zones";
import { roundReading, soilStatus } from "../lib/soilStatus";
import { plotToday } from "../lib/sowingDate";
import { soilLevel, type Level } from "../lib/statusLevel";
import type { HarvestInfo, SoilReading } from "./types";

export interface FarmSnapshot {
  chatLive: boolean;
  /** What answers: the live Muse Spark or a labeled replay (D094). Absent in older fixtures. */
  health?: HealthResponse;
  /** The forecast the gate reads (D095); null when the backend has none for the plot. */
  weather?: Weather | null;
  plot: Plot;
  clock: Clock;
  /** The zone the screens lead with: the one that needs the farmer most (lib/zones). */
  zone: Zone | null;
  /** Its soil moisture, oldest first. */
  readings: Reading[];
  /** Every zone of the plot with its readings, in the backend's order; a new demo plot has two (D089). */
  zones: ZoneSoil[];
  cycle: Cycle | null;
  /** The cycle's crop stages in order, from its catalogue entry (D077); empty without a cycle. */
  stageOrder: string[];
  /** The heat the crop needs to be ready; null without a catalogue entry. */
  maturityGdd: number | null;
  /** Stage 2 waters it; false for a manual record (D083). */
  automated: boolean;
  /** Sown outside the planner's top 3, by the farmer's choice. */
  ownRisk: boolean;
  /** What the planner said when it was sown. */
  planAtSowing: PlanAtSowing | null;
  tasks: Task[];
  notifications: Notification[];
  reports: Report[];
  stop: EmergencyStop;
  imagery: Imagery;
  verdicts: LogEvent[];
  executions: LogEvent[];
  failures: LogEvent[];
  rejections: LogEvent[];
  reverts: LogEvent[];
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

export function soilLevelOf(soil: SoilReading): Level {
  return soilLevel(soilStatus(soil.value, soil.fieldCapacity));
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

/** What the agronomist proposes besides water (D093): the farmer does it by hand. */
const FIELD_WORK = new Set(["fertilizer", "agrochemical", "scouting_visit", "stress_alert"]);

export function isFieldWork(task: Task): boolean {
  return FIELD_WORK.has(task.action_type);
}

/** "Urea, 100 kg/ha" for an input; null for a visit or an alert. */
export function doseOf(task: Task): string | null {
  const product = task.params.product;
  const dose = task.params.dose_kg_ha;
  if (typeof product !== "string") return null;
  return typeof dose === "number" ? en.fieldWork.dose(product, roundReading(dose)) : product;
}

/** The task as the farmer names it: "Fertilizer for Zone 2". */
export function fieldWorkTitle(task: Task, zone: string): string {
  const name = en.fieldWork.names[task.action_type] ?? en.fieldWork.other;
  return en.fieldWork.title(name, zone);
}

/**
 * Rain in the next 24 h: the forecast endpoint when there is one (D095), otherwise
 * the newest gate verdict of today. Null: nothing says, which is not "no rain".
 */
export function rainNext24h(snapshot: FarmSnapshot): number | null {
  const fromForecast = snapshot.weather?.rain_next_24h_mm;
  if (fromForecast !== undefined && fromForecast !== null) return roundRain(fromForecast);
  return forecastOfDay(snapshot.verdicts, snapshot.clock.now, plotOffset(snapshot));
}

/** The forecast's rain that falls on the plot-local day of `dayIso`; null when it does not cover it. */
export function rainOnDay(snapshot: FarmSnapshot, dayIso: string): number | null {
  const offset = plotOffset(snapshot);
  const day = plotDay(dayIso, offset);
  const hours = (snapshot.weather?.hours ?? []).filter(
    (hour) => plotDay(hour.hour_ending, offset) === day && hour.rain_mm !== null,
  );
  if (hours.length === 0) return null;
  return roundRain(hours.reduce((total, hour) => total + (hour.rain_mm ?? 0), 0));
}

function roundRain(mm: number): number {
  return Math.round(mm * 10) / 10;
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
  if (isFieldWork(task)) return en.fieldWork.question(fieldWorkTitle(task, zone));
  return en.task.other;
}

/** LIVE or REPLAY, as /health says it (D094); null for a backend that does not say. */
export function modeBadge(snapshot: FarmSnapshot): { live: boolean; text: string; title: string } | null {
  const health = snapshot.health;
  if (health === undefined) return null;
  const replay = health.llm_mode === "replay" || (health.llm_mode === undefined && health.mock_llm);
  return replay
    ? { live: false, text: en.mode.replay(health.replay?.recorded_on ?? null), title: en.mode.replayTitle }
    : { live: true, text: en.mode.live(health.agent_model ?? null), title: en.mode.liveTitle };
}

/** The farmer's name of the zone a task is for; the lead zone's when it has none. */
export function zoneNameOf(snapshot: FarmSnapshot, zoneId: number | null): string {
  const found = snapshot.zones.find((entry) => entry.zone.id === zoneId);
  return found === undefined ? zoneName(snapshot) : zoneLabel(found.zone.name);
}

export function plotOffset(snapshot: FarmSnapshot): number {
  return snapshot.plot.utc_offset_hours;
}

/** What the harvest form needs, while a crop grows. */
export function harvestInfo(snapshot: FarmSnapshot): HarvestInfo | null {
  const cycle = snapshot.cycle;
  if (cycle === null || cycle.status !== "active") return null;
  const open = snapshot.tasks.find(
    (task) => task.status === "pending_approval" || task.status === "scheduled",
  );
  return {
    cycleId: cycle.id,
    crop: cycle.crop,
    sowingDate: cycle.sowing_date,
    today: plotToday(snapshot.clock.now, plotOffset(snapshot)),
    areaHa: snapshot.plot.area_ha,
    openTask: open === undefined ? null : { id: open.id, decision: open.status === "pending_approval" },
  };
}
