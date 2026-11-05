// What the agent read to answer, from its trace in the event log. Pure logic only.
import type { LogEvent } from "../../types/api";

export type LookedAt = "soil" | "rain";

const SOURCES: Record<string, LookedAt> = {
  read_zone: "soil",
  consult_monitoring: "soil",
  read_forecast: "rain",
};

/** The sources one chat run used, each once, in the order it used them. */
export function lookedAtOfRun(events: readonly LogEvent[], runId: string): LookedAt[] {
  const found = new Set<LookedAt>();
  const calls = events
    .filter((event) => event.inputs.run_id === runId)
    .toSorted((a, b) => a.id - b.id);
  for (const call of calls) {
    const tool = call.inputs.tool;
    const source = typeof tool === "string" ? SOURCES[tool] : undefined;
    if (source !== undefined) found.add(source);
  }
  return [...found];
}

/** "0:04": how long a recording ran. */
export function clipLength(milliseconds: number): string {
  const seconds = Math.max(0, Math.round(milliseconds / 1000));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}
