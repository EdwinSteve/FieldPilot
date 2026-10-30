// The gate's verdict per task, from its gate_verdict event. Pure logic only.
import type { Json, LogEvent } from "../types/api";

export interface ParsedVerdict {
  requestedLevel: string;
  effectiveLevel: string;
  outcome: string;
  /** Rule codes that fired, in stored order. */
  violations: string[];
}

/** The stored verdict, or null when the event does not carry one. */
export function parseVerdictInputs(inputs: Record<string, Json>): ParsedVerdict | null {
  if (typeof inputs.verdict !== "object" || inputs.verdict === null || Array.isArray(inputs.verdict)) {
    return null;
  }
  const verdict = inputs.verdict as { [key: string]: Json };
  const requestedLevel = asString(verdict.requested_level);
  const effectiveLevel = asString(verdict.effective_level);
  const outcome = asString(verdict.outcome);
  if (requestedLevel === null || effectiveLevel === null || outcome === null) return null;
  if (!Array.isArray(verdict.violations)) return null;
  const violations: string[] = [];
  for (const item of verdict.violations) {
    if (typeof item === "object" && item !== null && !Array.isArray(item)) {
      const code = (item as { [key: string]: Json }).code;
      if (typeof code === "string") violations.push(code);
    }
  }
  return { requestedLevel, effectiveLevel, outcome, violations };
}

/** The latest event per task, for joining verdicts and failures onto tasks. */
export function eventsByTask(events: readonly LogEvent[]): Map<number, LogEvent> {
  const byTask = new Map<number, LogEvent>();
  for (const event of events) {
    if (event.task_id !== null) byTask.set(event.task_id, event);
  }
  return byTask;
}

function asString(value: Json | undefined): string | null {
  return typeof value === "string" ? value : null;
}
