import { describe, expect, it } from "vitest";
import type { CropOutlook, PlantingPlan } from "../api/lifecycle";
import { monthGrid, nothingGrowsWell, percent, rankOf, weekOf, yieldLevel } from "./plantingPlan";

function outlook(crop: string, p50: number): CropOutlook {
  return {
    crop,
    name_es: crop,
    sowing_date: "",
    harvest_date: "",
    rel_yield_p10: p50,
    rel_yield_p50: p50,
    rel_yield_p90: p50,
    p_success: 0.9,
    irrigation_mm_p50: 100,
    heat_days: 0,
    cold_days: 0,
    automatable: false,
  };
}

const plan: PlantingPlan = {
  plot_id: 2,
  generated_at: "2026-11-03T12:00:00Z",
  model: "planner-2026-11-03",
  site_built_on: "2026-11-03",
  weeks: [
    { sowing_date: "2026-11-23", weather_until: "", oni: 2, oni_latest_published: false, outlooks: [outlook("maize", 0.9), outlook("soybean", 0.8)] },
    { sowing_date: "2026-11-30", weather_until: "", oni: 2, oni_latest_published: false, outlooks: [outlook("soybean", 0.95), outlook("maize", 0.7)] },
    { sowing_date: "2026-12-07", weather_until: "", oni: 2, oni_latest_published: false, outlooks: [outlook("maize", 0.6), outlook("soybean", 0.5)] },
  ],
};

describe("the yield words", () => {
  it("rounds to a whole percent and bands it", () => {
    expect(percent(0.916)).toBe(92);
    expect(yieldLevel(0.7)).toBe("good");
    expect(yieldLevel(0.5)).toBe("fair");
    expect(yieldLevel(0.2)).toBe("poor");
  });
});

describe("nothingGrowsWell", () => {
  it("says so when even the best crop is under 45 %", () => {
    expect(nothingGrowsWell([outlook("potato", 0.25), outlook("common_bean", 0.25)])).toBe(true);
    expect(nothingGrowsWell([outlook("maize", 0.45), outlook("cotton", 0)])).toBe(false);
    expect(nothingGrowsWell([])).toBe(true);
  });
});

describe("monthGrid", () => {
  it("gives each crop its best sowing in each month", () => {
    expect(monthGrid(plan)).toEqual({
      months: ["2026-11", "2026-12"],
      rows: [
        {
          crop: "maize",
          cells: [
            { yieldP50: 0.9, sowingDate: "2026-11-23" },
            { yieldP50: 0.6, sowingDate: "2026-12-07" },
          ],
        },
        {
          crop: "soybean",
          cells: [
            { yieldP50: 0.95, sowingDate: "2026-11-30" },
            { yieldP50: 0.5, sowingDate: "2026-12-07" },
          ],
        },
      ],
    });
  });
});

describe("weekOf and rankOf", () => {
  it("finds the week a date falls in, and the crop's place in it", () => {
    const week = weekOf(plan, "2026-12-01");
    expect(week?.sowing_date).toBe("2026-11-30");
    expect(rankOf(week, "maize")).toBe(2);
    expect(rankOf(week, "cotton")).toBeNull();
  });

  it("falls back to the first week before the plan starts", () => {
    expect(weekOf(plan, "2026-11-01")?.sowing_date).toBe("2026-11-23");
  });
});
