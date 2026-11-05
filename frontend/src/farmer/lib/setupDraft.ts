// The farmer's setup answers, kept on the phone: the backend has no place for the
// crops they grow, their goals or the outline's corners (D083 keeps one point). Pure logic only.
import type { LatLng } from "./farmOutline";
import { GOALS, type Goal } from "./goals";

export interface SetupDraft {
  crops: string[];
  goals: Goal[];
  outline: LatLng[];
  farmName: string;
}

export const EMPTY_DRAFT: SetupDraft = { crops: [], goals: [], outline: [], farmName: "" };

const VERSION = 1;

function isPoint(value: unknown): value is LatLng {
  const point = value as Partial<LatLng> | null;
  return typeof point?.lat === "number" && typeof point.lng === "number";
}

const strings = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];

export function toStoredDraft(draft: SetupDraft): string {
  return JSON.stringify({ version: VERSION, ...draft });
}

export function fromStoredDraft(text: string | null): SetupDraft {
  try {
    const value = JSON.parse(text ?? "null") as Record<string, unknown> | null;
    if (value?.version !== VERSION) return EMPTY_DRAFT;
    return {
      crops: strings(value.crops),
      goals: strings(value.goals).filter((goal): goal is Goal => GOALS.includes(goal as Goal)),
      outline: Array.isArray(value.outline) ? value.outline.filter(isPoint) : [],
      farmName: typeof value.farmName === "string" ? value.farmName : "",
    };
  } catch {
    return EMPTY_DRAFT;
  }
}
