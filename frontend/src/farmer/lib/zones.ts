// Which zone the farm screens lead with when a plot has several (D089). Pure logic only.
import type { Reading, Zone } from "../../types/api";

/** A zone and its soil moisture readings, oldest first. */
export interface ZoneSoil {
  zone: Zone;
  readings: Reading[];
}

/** How full the zone's soil is by its latest reading, 0 to 1 or more; null without a reading. */
function fill(entry: ZoneSoil): number | null {
  const latest = entry.readings.at(-1);
  if (latest === undefined || !(entry.zone.field_capacity_pct > 0)) return null;
  return latest.value / entry.zone.field_capacity_pct;
}

/**
 * The zone that needs the farmer most: the driest for its soil. Zones with no reading
 * come after every zone with one; between equals, the first keeps its place.
 */
export function neediestZone(zones: readonly ZoneSoil[]): ZoneSoil | null {
  let best: ZoneSoil | null = null;
  let bestFill: number | null = null;
  for (const entry of zones) {
    const value = fill(entry);
    if (best === null || (value !== null && (bestFill === null || value < bestFill))) {
      best = entry;
      bestFill = value;
    }
  }
  return best;
}
