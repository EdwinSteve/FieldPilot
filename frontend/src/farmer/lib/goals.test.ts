import { describe, expect, it } from "vitest";
import type { CropOutlook } from "../api/lifecycle";
import { orderForGoals, toggleGoal } from "./goals";

function outlook(crop: string, p50: number, success: number, water: number): CropOutlook {
  return {
    crop,
    name_es: crop,
    sowing_date: "2026-11-09",
    harvest_date: "2027-03-01",
    rel_yield_p10: p50 - 0.1,
    rel_yield_p50: p50,
    rel_yield_p90: p50 + 0.1,
    p_success: success,
    irrigation_mm_p50: water,
    heat_days: 0,
    cold_days: 0,
    automatable: crop === "maize",
  };
}

/** As the backend ranks a week near La Plata: best yield first. */
const week = [
  outlook("maize", 0.92, 0.97, 157),
  outlook("soybean", 0.9, 0.999, 112),
  outlook("groundnut", 0.83, 0.996, 185),
  outlook("tomato", 0.71, 0.84, 194),
];
const crops = (list: CropOutlook[]) => list.map((o) => o.crop);

describe("orderForGoals", () => {
  it("keeps the backend's order without a goal", () => {
    expect(crops(orderForGoals(week, []))).toEqual(["maize", "soybean", "groundnut", "tomato"]);
  });

  it("puts the thirstless crop first to save water", () => {
    expect(crops(orderForGoals(week, ["save_water"]))).toEqual([
      "soybean",
      "maize",
      "groundnut",
      "tomato",
    ]);
  });

  it("puts the surest crop first to take less risk", () => {
    expect(crops(orderForGoals(week, ["less_risk"]))[0]).toBe("soybean");
  });

  it("puts a legume first to care for the soil", () => {
    expect(crops(orderForGoals(week, ["care_soil"])).slice(0, 2)).toEqual(["soybean", "groundnut"]);
  });

  it("never lifts a crop from outside the top three", () => {
    expect(crops(orderForGoals(week, ["save_water"])).at(-1)).toBe("tomato");
  });
});

describe("toggleGoal", () => {
  it("adds goals in the order tapped and removes a chosen one", () => {
    expect(toggleGoal(["save_water"], "less_risk")).toEqual(["save_water", "less_risk"]);
    expect(toggleGoal(["save_water", "less_risk"], "save_water")).toEqual(["less_risk"]);
  });
});
