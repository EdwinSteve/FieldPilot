import { describe, expect, it } from "vitest";
import { eventsByTask, parseVerdictInputs } from "./verdict";
import type { Json, LogEvent } from "../types/api";

function event(id: number, taskId: number | null, inputs: Record<string, Json>): LogEvent {
  return {
    id,
    kind: "gate_verdict",
    actor: "system:autonomy_gate",
    reason: "",
    occurred_at: "2026-10-28T11:00:00Z",
    task_id: taskId,
    autonomy_level: null,
    rule: null,
    inputs,
  };
}

const INPUTS: Record<string, Json> = {
  proposal: {},
  context: {},
  verdict: {
    outcome: "await_approval",
    requested_level: "autonomous",
    effective_level: "approval",
    reason_code: "rain_forecast_above_limit",
    violations: [{ code: "rain_forecast_above_limit", params: { rain_mm: 12 } }],
  },
};

describe("parseVerdictInputs", () => {
  it("reads levels, outcome and the rules that fired", () => {
    expect(parseVerdictInputs(INPUTS)).toEqual({
      requestedLevel: "autonomous",
      effectiveLevel: "approval",
      outcome: "await_approval",
      violations: ["rain_forecast_above_limit"],
    });
  });

  it("reads an allowed verdict with no violations", () => {
    const allowed = {
      verdict: {
        outcome: "execute",
        requested_level: "autonomous",
        effective_level: "autonomous",
        reason_code: null,
        violations: [],
      },
    };
    expect(parseVerdictInputs(allowed)?.violations).toEqual([]);
  });

  it("returns null without a stored verdict", () => {
    expect(parseVerdictInputs({})).toBeNull();
    expect(parseVerdictInputs({ verdict: null })).toBeNull();
    expect(parseVerdictInputs({ verdict: { outcome: "execute" } })).toBeNull();
  });

  it("skips malformed violations instead of dropping the verdict", () => {
    const inputs = {
      verdict: {
        outcome: "await_approval",
        requested_level: "autonomous",
        effective_level: "approval",
        reason_code: null,
        violations: [{ code: "rain_forecast_above_limit" }, null, { code: 42 }],
      },
    };
    expect(parseVerdictInputs(inputs)?.violations).toEqual(["rain_forecast_above_limit"]);
  });
});

describe("eventsByTask", () => {
  it("keeps the latest event per task and skips taskless ones", () => {
    const first = event(1, 7, INPUTS);
    const second = event(2, 7, INPUTS);
    const other = event(3, 9, INPUTS);
    const taskless = event(4, null, INPUTS);
    expect(eventsByTask([first, second, other, taskless])).toEqual(
      new Map([
        [7, second],
        [9, other],
      ]),
    );
  });
});
