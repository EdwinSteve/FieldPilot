// Reads facts out of an event's free-form `inputs`. Defensive: odd shapes read as null.
import type { Json, LogEvent } from "../../types/api";

type JsonObject = { [key: string]: Json };

function asObject(value: Json | undefined): JsonObject | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  return value;
}

function asNumber(value: Json | undefined): number | null {
  return typeof value === "number" ? value : null;
}

export interface GateFacts {
  soilPct: number | null;
  rainMm: number | null;
  proposedBy: string | null;
}

/** What the gate saw when it judged a proposal. */
export function gateFacts(verdict: LogEvent): GateFacts {
  const context = asObject(verdict.inputs.context);
  const proposal = asObject(verdict.inputs.proposal);
  const proposedBy = proposal?.proposed_by;
  return {
    soilPct: asNumber(context?.soil_moisture_vwc),
    rainMm: asNumber(context?.rain_forecast_mm_24h),
    proposedBy: typeof proposedBy === "string" ? proposedBy : null,
  };
}

export interface ExecutionFacts {
  startedAt: string | null;
  targetMm: number | null;
  rateMmPerHour: number | null;
}

export function executionFacts(execution: LogEvent): ExecutionFacts {
  const startedAt = execution.inputs.started_at;
  return {
    startedAt: typeof startedAt === "string" ? startedAt : null,
    targetMm: asNumber(execution.inputs.target_mm),
    rateMmPerHour: asNumber(execution.inputs.rate_mm_per_h),
  };
}

/** The forecast that blocked a scheduled task at its re-check (D033), when that was the cause. */
export function recheckRainMm(failure: LogEvent): number | null {
  const violations = asObject(failure.inputs.recheck_verdict)?.violations;
  if (!Array.isArray(violations)) return null;
  for (const violation of violations) {
    const forecast = asNumber(asObject(asObject(violation)?.params)?.forecast_mm);
    if (forecast !== null) return forecast;
  }
  return null;
}

/** True for the failure of a scheduled task the re-check refused (D033). */
export function isRecheckFailure(failure: LogEvent): boolean {
  return asObject(failure.inputs.recheck_verdict) !== null;
}

/** True for the notice that a watering may have run on after a restart (D032). */
export function isInterruptedWatering(notice: LogEvent): boolean {
  return notice.inputs.simulator_state_resumed === false;
}

/** The water already on the field when an undo stopped it (D007). */
export function appliedMm(revert: LogEvent): number {
  return asNumber(revert.inputs.applied_mm) ?? 0;
}

/** The farmer's own words for a "no", or null when they skipped the question. */
export function rejectionReason(rejection: LogEvent): string | null {
  const reason = rejection.inputs.reason;
  return typeof reason === "string" && reason !== "" ? reason : null;
}
