// The planting plan as the advice screen draws it. Pure logic only.
import type { CropOutlook, PlantingPlan, SowingWeek } from "../api/lifecycle";

export type YieldLevel = "good" | "fair" | "poor";

/** Of the potential yield under rain only: the bands the cells and bars are tinted by. */
const GOOD_YIELD = 0.7;
const FAIR_YIELD = 0.45;

export function percent(fraction: number): number {
  return Math.round(fraction * 100);
}

export function yieldLevel(fraction: number): YieldLevel {
  if (fraction >= GOOD_YIELD) return "good";
  return fraction >= FAIR_YIELD ? "fair" : "poor";
}

/** Even the week's best crop is poor: the top three are still the backend's, but none does well. */
export function nothingGrowsWell(outlooks: readonly CropOutlook[]): boolean {
  const best = Math.max(0, ...outlooks.map((outlook) => outlook.rel_yield_p50));
  return yieldLevel(best) === "poor";
}

/** The week a sowing date falls in: the last week starting on or before it. */
export function weekOf(plan: PlantingPlan, isoDate: string): SowingWeek | null {
  return plan.weeks.findLast((week) => week.sowing_date <= isoDate) ?? plan.weeks[0] ?? null;
}

export function outlookOf(week: SowingWeek | null, crop: string): CropOutlook | null {
  return week?.outlooks.find((outlook) => outlook.crop === crop) ?? null;
}

/** Its place in the backend's ranking of the week, 1 first; null when the planner did not judge it. */
export function rankOf(week: SowingWeek | null, crop: string): number | null {
  const index = week?.outlooks.findIndex((outlook) => outlook.crop === crop) ?? -1;
  return index < 0 ? null : index + 1;
}
