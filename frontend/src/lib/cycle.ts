// Where the last daily cycle got to, per pipeline step. Pure logic only.
import type { DailyCycleResult } from "../types/api";

export const CYCLE_STEPS = ["monitoring", "imaging", "irrigation", "reporting"] as const;

export type CycleStep = (typeof CYCLE_STEPS)[number];

/** done: completed · stopped: turn limit or pause · todo: never ran · idle: no cycle yet. */
export type StepState = "done" | "stopped" | "todo" | "idle";

/** One state per step, from the cycle response (or all idle before the first run). */
export function stepStates(result: DailyCycleResult | null): Record<CycleStep, StepState> {
  const states = {} as Record<CycleStep, StepState>;
  for (const step of CYCLE_STEPS) {
    if (result === null) {
      states[step] = "idle";
      continue;
    }
    const run = result.runs.find((r) => r.subagent === step);
    if (run === undefined) {
      states[step] = "todo";
    } else if (run.status === "completed") {
      states[step] = "done";
    } else {
      states[step] = "stopped";
    }
  }
  return states;
}

/** Turns each step took in the last cycle, for the "what it did" captions. */
export function stepTurns(result: DailyCycleResult | null): Record<CycleStep, number | null> {
  const turns = {} as Record<CycleStep, number | null>;
  for (const step of CYCLE_STEPS) {
    turns[step] = result?.runs.find((r) => r.subagent === step)?.turns ?? null;
  }
  return turns;
}
