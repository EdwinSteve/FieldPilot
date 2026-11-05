// How old the farm on screen is, in real time (not the simulated clock). Pure logic only.
import { en } from "../i18n/en";

const MINUTE_MS = 60_000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;

/** "just now", "4 min ago", "2 h ago" or "3 days ago". A clock that runs backwards reads as now. */
export function ageText(sinceMs: number, nowMs: number): string {
  const age = Math.max(0, nowMs - sinceMs);
  if (age < MINUTE_MS) return en.freshness.justNow;
  if (age < HOUR_MS) return en.freshness.minutes(Math.floor(age / MINUTE_MS));
  if (age < DAY_MS) return en.freshness.hours(Math.floor(age / HOUR_MS));
  return en.freshness.days(Math.floor(age / DAY_MS));
}
