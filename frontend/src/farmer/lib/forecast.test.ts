import { describe, expect, it } from "vitest";
import type { LogEvent } from "../../types/api";
import { forecastOfDay } from "./forecast";

const OFFSET = -5;

function verdict(occurredAt: string, rainMm: number | null): LogEvent {
  return {
    id: 1,
    kind: "gate_verdict",
    actor: "gate",
    reason: "r",
    occurred_at: occurredAt,
    task_id: 1,
    autonomy_level: null,
    rule: null,
    inputs: { context: { rain_forecast_mm_24h: rainMm } },
  };
}

describe("forecastOfDay", () => {
  const monday = verdict("2026-11-02T11:00:00Z", 12);

  it("reads the day's forecast", () => {
    expect(forecastOfDay([monday], "2026-11-02T13:00:00Z", OFFSET)).toBe(12);
  });

  it("does not carry yesterday's forecast into today", () => {
    expect(forecastOfDay([monday], "2026-11-03T11:00:00Z", OFFSET)).toBeNull();
  });

  it("takes the newest verdict of the day", () => {
    const later = verdict("2026-11-02T15:00:00Z", 3);
    expect(forecastOfDay([later, monday], "2026-11-02T16:00:00Z", OFFSET)).toBe(3);
  });

  it("keeps a real zero", () => {
    const dry = verdict("2026-11-03T11:00:00Z", 0);
    expect(forecastOfDay([dry], "2026-11-03T11:00:00Z", OFFSET)).toBe(0);
  });

  it("skips a verdict with no forecast", () => {
    const blind = verdict("2026-11-02T15:00:00Z", null);
    expect(forecastOfDay([monday, blind], "2026-11-02T16:00:00Z", OFFSET)).toBe(12);
  });
});
