import { describe, expect, it } from "vitest";
import type { LogEvent } from "../../types/api";
import { clipLength, lookedAtOfRun } from "./lookedAt";

function call(id: number, runId: string, tool: string | null): LogEvent {
  return {
    id,
    kind: "agent_tool_call",
    actor: "agent:orchestrator",
    reason: "r",
    occurred_at: "2026-11-02T11:00:00Z",
    task_id: null,
    autonomy_level: null,
    rule: null,
    inputs: { run_id: runId, tool },
  };
}

describe("lookedAtOfRun", () => {
  it("keeps only this run's sources, in order", () => {
    const events = [
      call(3, "r1", "read_forecast"),
      call(1, "r1", "read_zone"),
      call(2, "other", "read_forecast"),
    ];
    expect(lookedAtOfRun(events, "r1")).toEqual(["soil", "rain"]);
  });

  it("counts a monitoring consult as the soil, once", () => {
    const events = [call(1, "r1", "read_zone"), call(2, "r1", "consult_monitoring")];
    expect(lookedAtOfRun(events, "r1")).toEqual(["soil"]);
  });

  it("ignores what is not a field reading", () => {
    const events = [call(1, "r1", "answer_farmer"), call(2, "r1", null)];
    expect(lookedAtOfRun(events, "r1")).toEqual([]);
  });
});

describe("clipLength", () => {
  it.each([
    [4_000, "0:04"],
    [4_400, "0:04"],
    [65_000, "1:05"],
    [-10, "0:00"],
  ])("writes %s ms as %s", (milliseconds, text) => {
    expect(clipLength(milliseconds)).toBe(text);
  });
});
