// Whether the soil is getting wetter or drier, in the farmer's terms. Pure logic only.
import type { Reading } from "../../types/api";
import { soilFill } from "./soilFill";

export type TrendDirection = "up" | "down" | "steady";

export interface SoilTrend {
  direction: TrendDirection;
  /** The reading it is compared with. */
  previous: number;
}

/** Compared with about a day ago: readings an hour apart would only show noise. */
const COMPARE_AFTER_MS = 20 * 3_600_000;
const STEADY_WITHIN = 0.5;

/** Against the newest reading at least 20 hours older. Null with no such reading. */
export function soilTrend(readings: readonly Reading[], nowIso: string): SoilTrend | null {
  const now = Date.parse(nowIso);
  const past = readings.filter((reading) => Date.parse(reading.recorded_at) <= now);
  const latest = past.at(-1);
  if (latest === undefined) return null;
  const limit = Date.parse(latest.recorded_at) - COMPARE_AFTER_MS;
  const earlier = past.filter((reading) => Date.parse(reading.recorded_at) <= limit).at(-1);
  if (earlier === undefined) return null;
  const change = latest.value - earlier.value;
  if (Math.abs(change) < STEADY_WITHIN) return { direction: "steady", previous: earlier.value };
  return { direction: change > 0 ? "up" : "down", previous: earlier.value };
}

/** How full the soil is, as a whole percent of what it can hold: 20 of 32 is 63. */
export function percentFull(value: number, fieldCapacity: number): number {
  return Math.round(soilFill(value, fieldCapacity) * 100);
}
