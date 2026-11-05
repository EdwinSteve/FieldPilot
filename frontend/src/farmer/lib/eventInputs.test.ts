import { describe, expect, it } from "vitest";
import type { Json, LogEvent } from "../../types/api";
import {
  executionFacts,
  gateFacts,
  isInterruptedWatering,
  isRecheckFailure,
  recheckRainMm,
  rejectionReason,
} from "./eventInputs";

function event(inputs: Record<string, Json>): LogEvent {
  return {
    id: 1,
    kind: "x",
    actor: "a",
    reason: "r",
    occurred_at: "2026-11-02T11:00:00Z",
    task_id: 1,
    autonomy_level: null,
    rule: null,
    inputs,
  };
}

describe("gateFacts", () => {
  it("reads what the gate saw", () => {
    const verdict = event({
      context: { soil_moisture_vwc: 20, rain_forecast_mm_24h: 12 },
      proposal: { proposed_by: "agent:irrigation" },
    });
    expect(gateFacts(verdict)).toEqual({
      soilPct: 20,
      rainMm: 12,
      proposedBy: "agent:irrigation",
    });
  });

  it("reads an odd shape as unknown", () => {
    expect(gateFacts(event({ context: "nope" }))).toEqual({
      soilPct: null,
      rainMm: null,
      proposedBy: null,
    });
  });
});

describe("executionFacts", () => {
  it("reads the run", () => {
    const run = event({ started_at: "2026-11-03T11:00:00+00:00", target_mm: 20, rate_mm_per_h: 6 });
    expect(executionFacts(run)).toEqual({
      startedAt: "2026-11-03T11:00:00+00:00",
      targetMm: 20,
      rateMmPerHour: 6,
    });
  });
});

describe("the re-check of a scheduled task", () => {
  const failure = event({
    recheck_verdict: { violations: [{ code: "rain", params: { forecast_mm: 8 } }] },
  });

  it("finds the forecast that blocked it", () => {
    expect(isRecheckFailure(failure)).toBe(true);
    expect(recheckRainMm(failure)).toBe(8);
  });

  it("does not mistake another failure for it", () => {
    const other = event({ error: "valve stuck" });
    expect(isRecheckFailure(other)).toBe(false);
    expect(recheckRainMm(other)).toBeNull();
  });
});

describe("isInterruptedWatering", () => {
  it("is true only when the simulator did not resume", () => {
    expect(isInterruptedWatering(event({ simulator_state_resumed: false }))).toBe(true);
    expect(isInterruptedWatering(event({}))).toBe(false);
  });
});

describe("rejectionReason", () => {
  it("reads the words, or null when skipped", () => {
    expect(rejectionReason(event({ reason: "Wait for the rain" }))).toBe("Wait for the rain");
    expect(rejectionReason(event({ reason: null }))).toBeNull();
  });
});
