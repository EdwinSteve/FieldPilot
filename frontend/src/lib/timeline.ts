// The agent timeline: agent_tool_call events grouped by run, plan → act → observe (D045).
import type { Json, LogEvent } from "../types/api";

export interface TimelineTurn {
  eventId: number;
  turn: number;
  /** null for a text answer or a paused attempt. */
  tool: string | null;
  arguments: Json;
  result: Json;
  error: string | null;
  paused: boolean;
  durationMs: number;
  occurredAt: string;
}

export interface TimelineRun {
  runId: string;
  subagent: string;
  turns: TimelineTurn[];
  /** Last entry was a pause: the model did not answer (D048). */
  paused: boolean;
  refusals: number;
}

/** Runs in order of their first event; turns in log order. Other events are ignored. */
export function groupRuns(events: readonly LogEvent[]): TimelineRun[] {
  const runs = new Map<string, TimelineRun>();
  for (const event of events) {
    const turn = toTurn(event);
    const runId = asString(event.inputs.run_id);
    if (turn === null || runId === null || !event.actor.startsWith("agent:")) continue;
    const run = runs.get(runId) ?? {
      runId,
      subagent: event.actor.slice("agent:".length),
      turns: [],
      paused: false,
      refusals: 0,
    };
    run.turns.push(turn);
    run.paused = turn.paused;
    if (turn.error !== null && !turn.paused) run.refusals += 1;
    runs.set(runId, run);
  }
  return [...runs.values()];
}

function toTurn(event: LogEvent): TimelineTurn | null {
  if (event.kind !== "agent_tool_call") return null;
  const turn = event.inputs.turn;
  if (typeof turn !== "number") return null;
  const duration = event.inputs.duration_ms;
  return {
    eventId: event.id,
    turn,
    tool: asString(event.inputs.tool),
    arguments: event.inputs.arguments ?? null,
    result: event.inputs.result ?? null,
    error: asString(event.inputs.error),
    paused: event.inputs.pause !== null && event.inputs.pause !== undefined,
    durationMs: typeof duration === "number" ? duration : 0,
    occurredAt: event.occurred_at,
  };
}

function asString(value: Json | undefined): string | null {
  return typeof value === "string" ? value : null;
}

/** The subagent's name for the farmer. */
export const SUBAGENT_LABELS: Record<string, string> = {
  agronomist: "Agronomist · orchestrator",
  crop_health: "Crop health",
  soil_nutrition: "Soil nutrition",
  monitoring: "Monitoring",
  imaging: "Imaging",
  irrigation: "Irrigation",
  reporting: "Report",
  orchestrator: "Chat",
};

export type StoryFilter = "all" | "agent" | "gate" | "system";

export type EventCategory = "agent" | "gate" | "system";

const GATE_KINDS = new Set([
  "proposal",
  "gate_verdict",
  "execution_requested",
  "execution",
  "execution_failed",
  "revert",
  "revert_refused",
  "approval",
  "rejection",
]);

/** Agent work, gate-and-task decisions, or everything else (clock, scenarios, stops). */
export function eventCategory(kind: string): EventCategory {
  if (kind === "agent_tool_call") return "agent";
  if (GATE_KINDS.has(kind)) return "gate";
  return "system";
}

export interface StoryEntry {
  sortId: number;
  run: TimelineRun | null;
  event: LogEvent | null;
}

/**
 * Agent runs and single entries merged newest-first. Agent turns stay inside
 * their run; anything that is not a turn shows on its own, so nothing hides.
 */
export function storyEntries(
  events: readonly LogEvent[],
  filter: StoryFilter,
): StoryEntry[] {
  const runs = filter === "gate" || filter === "system" ? [] : groupRuns(events);
  const inRun = new Set<number>();
  for (const run of runs) {
    for (const turn of run.turns) inRun.add(turn.eventId);
  }
  const entries: StoryEntry[] = runs.map((run) => ({
    sortId: Math.max(...run.turns.map((turn) => turn.eventId)),
    run,
    event: null,
  }));
  for (const event of events) {
    if (inRun.has(event.id)) continue;
    if (filter !== "all" && eventCategory(event.kind) !== filter) continue;
    entries.push({ sortId: event.id, run: null, event });
  }
  return entries.toSorted((a, b) => b.sortId - a.sortId);
}
