import { describe, expect, it } from "vitest";
import type { LogEvent } from "../../types/api";
import { newestRecent } from "./recentEvent";

const NOW = "2026-11-03T11:00:00Z";

function event(id: number, occurredAt: string): LogEvent {
  return {
    id,
    kind: "x",
    actor: "a",
    reason: "r",
    occurred_at: occurredAt,
    task_id: null,
    autonomy_level: null,
    rule: null,
    inputs: {},
  };
}

describe("newestRecent", () => {
  it("takes the newest, whatever the order", () => {
    const events = [event(1, "2026-11-03T08:00:00Z"), event(2, "2026-11-03T10:00:00Z")];
    expect(newestRecent(events, NOW)?.id).toBe(2);
    expect(newestRecent(events.toReversed(), NOW)?.id).toBe(2);
  });

  it("keeps an event up to a day old", () => {
    expect(newestRecent([event(1, "2026-11-02T11:00:00Z")], NOW)?.id).toBe(1);
  });

  it("drops an older one", () => {
    expect(newestRecent([event(1, "2026-11-02T10:59:59Z")], NOW)).toBeNull();
  });

  it("ignores what has not happened on the simulated clock", () => {
    expect(newestRecent([event(1, "2026-11-03T11:00:01Z")], NOW)).toBeNull();
  });

  it("is null with no events", () => {
    expect(newestRecent([], NOW)).toBeNull();
  });
});
