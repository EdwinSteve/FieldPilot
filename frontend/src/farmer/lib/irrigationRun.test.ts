import { describe, expect, it } from "vitest";
import type { Json, LogEvent, Task, TaskStatus } from "../../types/api";
import { activeRun, irrigationRun } from "./irrigationRun";

function execution(inputs: Record<string, Json>): LogEvent {
  return {
    id: 1,
    kind: "execution",
    actor: "executor",
    reason: "r",
    occurred_at: "2026-11-03T11:00:00Z",
    task_id: 2,
    autonomy_level: null,
    rule: null,
    inputs,
  };
}

function task(status: TaskStatus): Task {
  return { id: 2, status } as Task;
}

const WATERING = execution({
  started_at: "2026-11-03T11:00:00+00:00",
  target_mm: 20,
  rate_mm_per_h: 6,
});

describe("irrigationRun", () => {
  it("ends when the water is applied: 20 mm at 6 mm/h is 3 h 20 min", () => {
    expect(irrigationRun(WATERING)?.endsAt).toBe("2026-11-03T14:20:00.000Z");
  });

  it("ignores a command that adds no water", () => {
    const closing = execution({
      started_at: "2026-11-03T11:00:00+00:00",
      target_mm: 0,
      rate_mm_per_h: 6,
    });
    expect(irrigationRun(closing)).toBeNull();
  });
});

describe("activeRun", () => {
  it("is on from the start until just before the end", () => {
    expect(activeRun([WATERING], [task("executed")], [], "2026-11-03T11:00:00Z")).not.toBeNull();
    expect(activeRun([WATERING], [task("executed")], [], "2026-11-03T14:19:59Z")).not.toBeNull();
  });

  it("is off once the water is applied", () => {
    expect(activeRun([WATERING], [task("executed")], [], "2026-11-03T14:20:00Z")).toBeNull();
  });

  it("is off once a stop command closed the valve", () => {
    const stop = {
      ...execution({ action_type: "stop_irrigation", target_mm: 0, rate_mm_per_h: 6 }),
      task_id: 9,
      occurred_at: "2026-11-03T12:00:00Z",
    };
    expect(
      activeRun([WATERING, stop], [task("executed")], [], "2026-11-03T12:30:00Z"),
    ).toBeNull();
  });

  it("is off once a restart cut the run off", () => {
    const notice = { ...WATERING, kind: "notification", inputs: { simulator_state_resumed: false } };
    expect(
      activeRun([WATERING], [task("executed")], [notice], "2026-11-03T12:00:00Z"),
    ).toBeNull();
  });

  it("is off for a reverted task", () => {
    expect(activeRun([WATERING], [task("reverted")], [], "2026-11-03T12:00:00Z")).toBeNull();
  });
});
