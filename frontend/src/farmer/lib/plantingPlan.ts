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

export interface MonthCell {
  /** The best expected yield of a sowing that month. */
  yieldP50: number;
  /** The week that gives it. */
  sowingDate: string;
}

export interface MonthRow {
  crop: string;
  cells: (MonthCell | null)[];
}

export interface MonthGrid {
  /** "2026-11", in order. */
  months: string[];
  /** Crops in the first week's order. */
  rows: MonthRow[];
}

const monthOf = (isoDate: string) => isoDate.slice(0, 7);

function bestIn(weeks: readonly SowingWeek[], crop: string): MonthCell | null {
  let best: MonthCell | null = null;
  for (const week of weeks) {
    const outlook = week.outlooks.find((candidate) => candidate.crop === crop);
    if (outlook !== undefined && (best === null || outlook.rel_yield_p50 > best.yieldP50)) {
      best = { yieldP50: outlook.rel_yield_p50, sowingDate: week.sowing_date };
    }
  }
  return best;
}

/** Each crop's best sowing in each month the plan covers: "what to sow when". */
export function monthGrid(plan: PlantingPlan): MonthGrid {
  const months = [...new Set(plan.weeks.map((week) => monthOf(week.sowing_date)))];
  const crops = plan.weeks[0]?.outlooks.map((outlook) => outlook.crop) ?? [];
  return {
    months,
    rows: crops.map((crop) => ({
      crop,
      cells: months.map((month) =>
        bestIn(
          plan.weeks.filter((week) => monthOf(week.sowing_date) === month),
          crop,
        ),
      ),
    })),
  };
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
