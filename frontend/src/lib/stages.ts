// The crop's walk through its stages, and the days since sowing. Pure logic only.
// The stage order comes from the crop's catalogue entry (GET /crops/{crop}, D077).

export type StageState = "done" | "current" | "todo";

export interface RecordedStage {
  name: string;
  ended_at: string | null;
}

export interface StageStep {
  name: string;
  state: StageState;
}

/** Each stage of the crop, in `order`, as done, current or still ahead. Unknown names are ignored. */
export function stageProgress(
  order: readonly string[],
  recorded: readonly RecordedStage[],
): StageStep[] {
  const byName = new Map(recorded.map((stage) => [stage.name, stage]));
  const current = order.find((name) => {
    const stage = byName.get(name);
    return stage !== undefined && stage.ended_at === null;
  });
  return order.map((name) => {
    const stage = byName.get(name);
    if (stage === undefined) return { name, state: "todo" };
    if (stage.ended_at !== null) return { name, state: "done" };
    return { name, state: name === current ? "current" : "done" };
  });
}

/** Whole days from sowing to the plot-local now. Never negative. */
export function daysSinceSowing(sowingDate: string, nowIso: string, utcOffsetHours: number): number {
  const sowing = Date.parse(`${sowingDate}T00:00:00Z`);
  const shifted = new Date(Date.parse(nowIso) + utcOffsetHours * 3_600_000);
  if (!Number.isFinite(sowing) || !Number.isFinite(shifted.getTime())) return 0;
  const startOfToday = Date.UTC(shifted.getUTCFullYear(), shifted.getUTCMonth(), shifted.getUTCDate());
  return Math.max(0, Math.floor((startOfToday - sowing) / 86_400_000));
}
