// What the farmer wants most, and how it orders the recommended crops. Pure logic only.
//
// The backend's top three stay the top three (D083 checks the sowing against
// them); the farmer's first goal only orders those three.
import type { CropOutlook } from "../api/lifecycle";

export type Goal = "save_water" | "earn_more" | "care_soil" | "less_risk";

/** The four goals, in the order the questionnaire first shows them. */
export const GOALS: readonly Goal[] = ["save_water", "earn_more", "care_soil", "less_risk"];

/** The backend calls the first three of a week "recommended" (docs/api.md §4). */
export const RECOMMENDED = 3;

/** Beans, soy and groundnut fix nitrogen and leave the soil richer (FAO, legumes in rotation). */
const LEGUMES = new Set(["common_bean", "soybean", "groundnut"]);

/** Higher is better for the goal. */
function fit(outlook: CropOutlook, goal: Goal): number {
  switch (goal) {
    case "save_water":
      return -outlook.irrigation_mm_p50;
    case "earn_more":
      return outlook.rel_yield_p50;
    case "less_risk":
      return outlook.p_success + outlook.rel_yield_p10 / 10;
    case "care_soil":
      return (LEGUMES.has(outlook.crop) ? 1 : 0) + outlook.rel_yield_p50 / 10;
  }
}

/** The week's crops, the recommended three ordered by the first goal, the others as the backend ranked them. */
export function orderForGoals(outlooks: readonly CropOutlook[], goals: readonly Goal[]): CropOutlook[] {
  const goal = goals[0];
  const top = outlooks.slice(0, RECOMMENDED);
  const ordered = goal === undefined ? top : top.toSorted((a, b) => fit(b, goal) - fit(a, goal));
  return [...ordered, ...outlooks.slice(RECOMMENDED)];
}

export function isLegume(crop: string): boolean {
  return LEGUMES.has(crop);
}

/** Tapping a goal adds it next; tapping a chosen one takes it out, and the later ones move up. */
export function toggleGoal(goals: readonly Goal[], goal: Goal): Goal[] {
  return goals.includes(goal) ? goals.filter((chosen) => chosen !== goal) : [...goals, goal];
}
