// Whether the soil sensor still reports. A display rule only.

const STALE_AFTER_MS = 48 * 3_600_000;

/** True when the newest reading is too old to trust. */
export function sensorIsStale(recordedAt: string, nowIso: string): boolean {
  return Date.parse(nowIso) - Date.parse(recordedAt) > STALE_AFTER_MS;
}
