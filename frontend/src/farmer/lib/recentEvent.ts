// Picks the event still worth showing. Pure logic only.
import type { LogEvent } from "../../types/api";

const STILL_NEWS_MS = 24 * 3_600_000;

/** The newest event of the last day, or null: an old alarm must not stay up for good. */
export function newestRecent(events: readonly LogEvent[], nowIso: string): LogEvent | null {
  const now = Date.parse(nowIso);
  let newest: LogEvent | null = null;
  for (const event of events) {
    const at = Date.parse(event.occurred_at);
    if (at > now || now - at > STILL_NEWS_MS) continue;
    if (newest === null || at > Date.parse(newest.occurred_at)) newest = event;
  }
  return newest;
}
