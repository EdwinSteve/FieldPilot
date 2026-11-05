// When the farmer says they sowed, as POST /plots/{id}/cycles accepts it (D083). Pure logic only.
import { plotDay } from "../../lib/format";

export type SowingDateProblem = "missing" | "future" | "too_old";

/** The backend accepts a sowing up to 60 days back (MAX_BACKDATE_DAYS). */
export const MAX_DAYS_BACK = 60;
const DAY_MS = 86_400_000;

/** The plot's calendar day now, "2026-11-02": the backend's own today. */
export function plotToday(nowIso: string, utcOffsetHours: number): string {
  return plotDay(nowIso, utcOffsetHours);
}

/** The first day the farmer may say they sowed on. */
export function earliestSowing(today: string): string {
  return new Date(Date.parse(`${today}T00:00:00Z`) - MAX_DAYS_BACK * DAY_MS)
    .toISOString()
    .slice(0, 10);
}

export function sowingDateProblem(date: string, today: string): SowingDateProblem | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return "missing";
  if (date > today) return "future";
  return date < earliestSowing(today) ? "too_old" : null;
}
