// The rain forecast, as the gate last read it. No endpoint serves it directly.
import { plotDay } from "../../lib/format";
import type { LogEvent } from "../../types/api";
import { gateFacts } from "./eventInputs";

/**
 * The forecast of the plot-local day of `dayIso`, from that day's newest gate
 * verdict. An older day's forecast is stale, so a day with no verdict is unknown.
 */
export function forecastOfDay(
  verdicts: readonly LogEvent[],
  dayIso: string,
  utcOffsetHours: number,
): number | null {
  const day = plotDay(dayIso, utcOffsetHours);
  let newest: { at: number; rainMm: number } | null = null;
  for (const verdict of verdicts) {
    if (plotDay(verdict.occurred_at, utcOffsetHours) !== day) continue;
    const { rainMm } = gateFacts(verdict);
    const at = Date.parse(verdict.occurred_at);
    if (rainMm !== null && (newest === null || at >= newest.at)) newest = { at, rainMm };
  }
  return newest?.rainMm ?? null;
}
