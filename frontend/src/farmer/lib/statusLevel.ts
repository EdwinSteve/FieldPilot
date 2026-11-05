// How good or bad something is, in one scale every screen shares. Pure logic only.
import type { SoilStatus } from "./soilStatus";

/** Rain and other plain facts are `info`: they are neither good nor bad by themselves. */
export type Level = "good" | "watch" | "bad" | "info" | "neutral";

const SOIL_LEVELS: Record<SoilStatus, Level> = {
  very_dry: "bad",
  dry: "watch",
  ok: "good",
  wet: "watch",
};

export function soilLevel(status: SoilStatus): Level {
  return SOIL_LEVELS[status];
}

/** Weak plants are a warning, not an alarm. Null means there is no photo to judge. */
export function plantsLevel(lowVigor: boolean | null): Level {
  if (lowVigor === null) return "neutral";
  return lowVigor ? "watch" : "good";
}

const SEVERITY: Level[] = ["bad", "watch", "good"];

/** The most serious of the levels that judge something; neutral when none does. */
export function worstLevel(levels: readonly Level[]): Level {
  return SEVERITY.find((level) => levels.includes(level)) ?? "neutral";
}
