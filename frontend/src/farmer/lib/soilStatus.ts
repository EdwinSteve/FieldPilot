// How dry the soil reads to the farmer. A display rule only: the gate decides watering.
import { gaugeFraction } from "../../lib/gauge";

export type SoilStatus = "very_dry" | "dry" | "ok" | "wet";

const VERY_DRY_BELOW = 0.55;
const DRY_BELOW = 0.7;

export function soilStatus(value: number, fieldCapacity: number): SoilStatus {
  const fraction = gaugeFraction(value, fieldCapacity);
  if (fraction < VERY_DRY_BELOW) return "very_dry";
  if (fraction < DRY_BELOW) return "dry";
  return fraction >= 1 ? "wet" : "ok";
}

/** Percentage points missing to field capacity, rounded. Never negative. */
export function pointsToFull(value: number, fieldCapacity: number): number {
  return Math.max(0, Math.round(fieldCapacity - value));
}

/** One decimal at most, as the farmer reads it: 16.737 is 16.7 and 20.0 is 20. */
export function roundReading(value: number): number {
  return Math.round(value * 10) / 10;
}
