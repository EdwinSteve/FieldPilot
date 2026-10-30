import { describe, expect, it } from "vitest";
import type { Json, LogEvent } from "../types/api";
import { groupRuns } from "./timeline";

let nextId = 1;

function call(
  runId: string,
  turn: number,
  inputs: Record<string, Json>,
  actor = "agent:monitoring",
): LogEvent {
  return {
    id: nextId++,
    kind: "agent_tool_call",
    actor,
    reason: "",
    occurred_at: "2026-10-28T11:00:00Z",
    task_id: null,
    autonomy_level: null,
    rule: null,
    inputs: { run_id: runId, turn, tool: null, arguments: null, result: null, error: null, pause: null, duration_ms: 5, ...inputs },
  };
}

describe("groupRuns", () => {
  it("groups turns by run, in log order, with plan, act and observe", () => {
    const runs = groupRuns([
      call("s1-monitoring", 1, { tool: "read_zone", arguments: { zone_id: 1 }, result: { value: 20 } }),
      call("s1-irrigation", 1, { tool: "propose_action" }, "agent:irrigation"),
      call("s1-monitoring", 2, { tool: "submit_assessment", result: { accepted: true } }),
    ]);

    expect(runs.map((r) => [r.runId, r.subagent, r.turns.length])).toEqual([
      ["s1-monitoring", "monitoring", 2],
      ["s1-irrigation", "irrigation", 1],
    ]);
    const first = runs[0]?.turns[0];
    expect(first?.tool).toBe("read_zone");
    expect(first?.arguments).toEqual({ zone_id: 1 });
    expect(first?.result).toEqual({ value: 20 });
    expect(first?.durationMs).toBe(5);
  });

  it("counts refusals and marks a run whose last entry is a pause", () => {
    const [run] = groupRuns([
      call("r", 1, { tool: "submit_report", error: "Report refused (1 of 3)" }),
      call("r", 2, { error: "LLMUnavailableError", pause: 1 }),
    ]);

    expect(run?.refusals).toBe(1);
    expect(run?.paused).toBe(true);
    expect(run?.turns[1]?.paused).toBe(true);
  });

  it("a run resumed after a pause is no longer paused", () => {
    const [run] = groupRuns([
      call("r", 1, { error: "LLMUnavailableError", pause: 1 }),
      call("r", 1, { tool: "read_zone" }),
    ]);

    expect(run?.paused).toBe(false);
    expect(run?.refusals).toBe(0);
  });

  it("ignores other event kinds and the cycle's own log entries", () => {
    const cycleEntry = call("s1", 0, {}, "system:daily_cycle");
    const other: LogEvent = { ...call("s1-monitoring", 1, {}), kind: "gate_verdict" };

    expect(groupRuns([cycleEntry, other])).toEqual([]);
  });
});
