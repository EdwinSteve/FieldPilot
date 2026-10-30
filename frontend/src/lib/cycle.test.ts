import { describe, expect, it } from "vitest";
import { contextStates, stepStates, stepTurns } from "./cycle";
import type { DailyCycleResult } from "../types/api";

function cycle(
  runs: [string, string, number][],
  stoppedAt: string | null = null,
): DailyCycleResult {
  return {
    session_id: "s1",
    status: stoppedAt === null ? "completed" : "turn_limit",
    stopped_at: stoppedAt,
    runs: runs.map(([subagent, status, turns]) => ({
      run_id: `${subagent}-1`,
      subagent,
      status,
      turns,
    })),
    brief: {},
  };
}

const FULL = cycle([
  ["monitoring", "completed", 6],
  ["imaging", "completed", 3],
  ["irrigation", "completed", 8],
  ["reporting", "completed", 4],
]);

describe("stepStates", () => {
  it("is idle before the first cycle", () => {
    expect(stepStates(null)).toEqual({
      monitoring: "idle",
      imaging: "idle",
      irrigation: "idle",
      reporting: "idle",
    });
  });

  it("marks every step done after a full cycle", () => {
    expect(stepStates(FULL)).toEqual({
      monitoring: "done",
      imaging: "done",
      irrigation: "done",
      reporting: "done",
    });
  });

  it("stops at the failed step and leaves the rest todo", () => {
    const result = cycle(
      [
        ["monitoring", "completed", 6],
        ["imaging", "completed", 3],
        ["irrigation", "turn_limit", 12],
      ],
      "irrigation",
    );
    expect(stepStates(result)).toEqual({
      monitoring: "done",
      imaging: "done",
      irrigation: "stopped",
      reporting: "todo",
    });
  });

  it("treats a pause as stopped", () => {
    const result = cycle([["monitoring", "paused", 2]], "monitoring");
    expect(stepStates(result).monitoring).toBe("stopped");
  });
});

describe("stepTurns", () => {
  it("reads each step's turns, null when it never ran", () => {
    expect(stepTurns(FULL)).toEqual({ monitoring: 6, imaging: 3, irrigation: 8, reporting: 4 });
    expect(stepTurns(null).monitoring).toBeNull();
  });
});

describe("contextStates", () => {
  it("is idle before the first cycle", () => {
    expect(contextStates(null)).toEqual({ sources: "idle", gate: "idle" });
  });

  it("marks sources read and the gate passed as the cycle advances", () => {
    const partial = cycle(
      [
        ["monitoring", "completed", 6],
        ["irrigation", "turn_limit", 12],
      ],
      "irrigation",
    );
    expect(contextStates(partial)).toEqual({ sources: "done", gate: "todo" });
    expect(contextStates(FULL)).toEqual({ sources: "done", gate: "done" });
  });
});
