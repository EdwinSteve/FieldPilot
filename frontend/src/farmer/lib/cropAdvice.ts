// A crop's outlook in plain words: a verdict, four facts and one reason. Pure logic only.
//
// The bands are a FieldPilot convention for reading the planner's numbers, not
// agronomy: the numbers stay on screen, under the words, as the proof.
import type { CropOutlook, PlantingPlan } from "../api/lifecycle";
import { RECOMMENDED } from "./goals";
import { yieldLevel, type YieldLevel } from "./plantingPlan";

export type Verdict = "good" | "okay" | "poor";
export type HarvestSize = "big" | "medium" | "small";
export type Chance = "very_likely" | "maybe" | "risky";
export type WaterNeed = "little" | "some" | "a_lot";
/** What holds a poor or okay crop back, when the planner's numbers say. */
export type Cause = "too_hot" | "too_cold" | "small_harvest" | "often_fails" | null;

const LIKELY = 0.8;
const MAYBE = 0.5;
/** Extra water on top of the rain over the whole cycle, in mm. */
const LITTLE_WATER_MM = 100;
const SOME_WATER_MM = 200;
/** A month of stress days in a cycle is what the farmer would notice. */
const STRESS_DAYS = 30;
/** Within 5 points of the best week, sowing sooner is worth more than waiting. */
const NEAR_BEST = 0.05;

const HARVEST: Record<YieldLevel, HarvestSize> = { good: "big", fair: "medium", poor: "small" };
const RANK: Record<Verdict, number> = { good: 0, okay: 1, poor: 2 };

export function harvestSize(outlook: CropOutlook): HarvestSize {
  return HARVEST[yieldLevel(outlook.rel_yield_p50)];
}

export function chance(outlook: CropOutlook): Chance {
  if (outlook.p_success >= LIKELY) return "very_likely";
  return outlook.p_success >= MAYBE ? "maybe" : "risky";
}

export function waterNeed(outlook: CropOutlook): WaterNeed {
  if (outlook.irrigation_mm_p50 < LITTLE_WATER_MM) return "little";
  return outlook.irrigation_mm_p50 < SOME_WATER_MM ? "some" : "a_lot";
}

/** The worse of how much it gives and how sure that is. */
export function verdict(outlook: CropOutlook): Verdict {
  const fromHarvest: Verdict = { big: "good", medium: "okay", small: "poor" }[harvestSize(outlook)] as Verdict;
  const fromChance: Verdict = { very_likely: "good", maybe: "okay", risky: "poor" }[chance(outlook)] as Verdict;
  return RANK[fromHarvest] >= RANK[fromChance] ? fromHarvest : fromChance;
}

/** Why a crop is not a good choice, the clearest cause first; null for a good one. */
export function cause(outlook: CropOutlook): Cause {
  if (verdict(outlook) === "good") return null;
  if (outlook.heat_days >= STRESS_DAYS) return "too_hot";
  if (outlook.cold_days >= STRESS_DAYS) return "too_cold";
  return harvestSize(outlook) === "small" ? "small_harvest" : "often_fails";
}

export type WeekMark = YieldLevel;

export interface WeekStrip {
  crop: string;
  /** One per sowing week, in order: its band, and its expected harvest from 0 to 1. */
  weeks: { date: string; mark: WeekMark; yield: number }[];
  /** The soonest week whose harvest is near the biggest; null when even that week is poor. */
  best: number | null;
}

/** A crop's twelve sowing weeks as marks, and the soonest one that is about as good as the best. */
export function weekStrip(plan: PlantingPlan, crop: string): WeekStrip {
  const weeks = plan.weeks.map((week) => {
    const outlook = week.outlooks.find((candidate) => candidate.crop === crop);
    return { date: week.sowing_date, yield: outlook?.rel_yield_p50 ?? 0 };
  });
  const top = Math.max(0, ...weeks.map((week) => week.yield));
  const soonest = Math.max(0, weeks.findIndex((week) => week.yield >= top - NEAR_BEST));
  return {
    crop,
    weeks: weeks.map((week) => ({ date: week.date, mark: yieldLevel(week.yield), yield: week.yield })),
    best: yieldLevel(top) === "poor" ? null : soonest,
  };
}

/** A thin bar of the strip: a real sowing week, or a step between two of them. */
export interface Bar {
  yield: number;
  mark: WeekMark;
  /** The sowing week this bar is, or null for a step in between. */
  week: number | null;
}

/**
 * The strip as many thin bars: each real week, then `between` bars stepping
 * evenly to the next week, like a line drawn as bars. Only real weeks carry a
 * week number, so the tick and the months always sit on the planner's own values.
 */
export function smoothBars(strip: WeekStrip, between = 3): Bar[] {
  return strip.weeks.flatMap((week, index) => {
    const bars: Bar[] = [{ yield: week.yield, mark: week.mark, week: index }];
    const next = strip.weeks[index + 1];
    if (next === undefined) return bars;
    for (let step = 1; step <= between; step += 1) {
      const value = week.yield + ((next.yield - week.yield) * step) / (between + 1);
      bars.push({ yield: value, mark: yieldLevel(value), week: null });
    }
    return bars;
  });
}

/**
 * The farmer's own crops first, as the backend ranks this week; without any,
 * the week's recommended three. The rest wait behind "Show other crops".
 */
export function stripCrops(plan: PlantingPlan, grown: readonly string[]): { mine: string[]; others: string[] } {
  const ranked = plan.weeks[0]?.outlooks.map((outlook) => outlook.crop) ?? [];
  const mine = ranked.filter((crop) => grown.includes(crop));
  const shown = mine.length > 0 ? mine : ranked.slice(0, RECOMMENDED);
  return { mine: shown, others: ranked.filter((crop) => !shown.includes(crop)) };
}
