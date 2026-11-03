import { describe, expect, it } from "vitest";
import type { CropOutlook, PlantingPlan } from "../api/lifecycle";
import {
  cause,
  chance,
  harvestSize,
  smoothBars,
  stripCrops,
  verdict,
  waterNeed,
  weekStrip,
} from "./cropAdvice";

function outlook(crop: string, p50: number, success: number, water = 100, heat = 0, cold = 0): CropOutlook {
  return {
    crop,
    name_es: crop,
    sowing_date: "2026-11-02",
    harvest_date: "2027-02-01",
    rel_yield_p10: p50 - 0.1,
    rel_yield_p50: p50,
    rel_yield_p90: p50 + 0.1,
    p_success: success,
    irrigation_mm_p50: water,
    heat_days: heat,
    cold_days: cold,
    automatable: false,
  };
}

describe("the plain words", () => {
  it("sizes the harvest, the chance and the water", () => {
    expect(harvestSize(outlook("x", 0.92, 1))).toBe("big");
    expect(harvestSize(outlook("x", 0.5, 1))).toBe("medium");
    expect(harvestSize(outlook("x", 0.2, 1))).toBe("small");
    expect(chance(outlook("x", 1, 0.93))).toBe("very_likely");
    expect(chance(outlook("x", 1, 0.6))).toBe("maybe");
    expect(chance(outlook("x", 1, 0.27))).toBe("risky");
    expect(waterNeed(outlook("x", 1, 1, 49))).toBe("little");
    expect(waterNeed(outlook("x", 1, 1, 142))).toBe("some");
    expect(waterNeed(outlook("x", 1, 1, 306))).toBe("a_lot");
  });
});

describe("verdict", () => {
  it("is good only when the harvest is big and likely", () => {
    expect(verdict(outlook("soybean", 0.72, 0.93))).toBe("good");
  });

  it("takes the worse of the two", () => {
    expect(verdict(outlook("groundnut", 0.64, 0.58))).toBe("okay");
    expect(verdict(outlook("maize", 0.56, 0.27))).toBe("poor");
    expect(verdict(outlook("potato", 0.25, 0))).toBe("poor");
  });
});

describe("cause", () => {
  it("has none for a good crop", () => {
    expect(cause(outlook("soybean", 0.72, 0.93))).toBeNull();
  });

  it("names heat or cold first, as the planner counted them", () => {
    expect(cause(outlook("potato", 0.15, 0, 320, 129.7))).toBe("too_hot");
    expect(cause(outlook("sorghum", 0.19, 0, 149, 0.2, 39.7))).toBe("too_cold");
  });

  it("otherwise says whether it gives little or often fails", () => {
    expect(cause(outlook("maize", 0.1, 0, 0, 7.1))).toBe("small_harvest");
    expect(cause(outlook("maize", 0.56, 0.27))).toBe("often_fails");
  });
});

const plan: PlantingPlan = {
  plot_id: 2,
  generated_at: "",
  model: "planner-2026-11-03",
  site_built_on: "",
  weeks: [0.5, 0.9, 0.2].map((maize, index) => ({
    sowing_date: `2026-11-0${index + 2}`,
    weather_until: "",
    oni: 2,
    oni_latest_published: false,
    outlooks: [outlook("soybean", 0.8, 1), outlook("maize", maize, 1), outlook("cotton", 0.1, 0)],
  })),
};

describe("weekStrip", () => {
  it("marks each sowing week and finds the best", () => {
    expect(weekStrip(plan, "maize")).toEqual({
      crop: "maize",
      weeks: [
        { date: "2026-11-02", mark: "fair", yield: 0.5 },
        { date: "2026-11-03", mark: "good", yield: 0.9 },
        { date: "2026-11-04", mark: "poor", yield: 0.2 },
      ],
      best: 1,
    });
  });
});

describe("weekStrip's best week", () => {
  it("is the soonest week within 5 points of the best, not a far one a little better", () => {
    const near: PlantingPlan = {
      ...plan,
      weeks: [0.88, 0.8, 0.9].map((maize, index) => ({
        sowing_date: `2026-11-0${index + 2}`,
        weather_until: "",
        oni: 2,
        oni_latest_published: false,
        outlooks: [outlook("maize", maize, 1)],
      })),
    };
    expect(weekStrip(near, "maize").best).toBe(0);
  });

  it("is none when even the best week is poor", () => {
    expect(weekStrip(plan, "cotton").best).toBeNull();
  });
});

describe("smoothBars", () => {
  it("steps evenly between real weeks and ends on the last one", () => {
    const bars = smoothBars(weekStrip(plan, "maize"), 1);
    expect(bars.map((bar) => [Number(bar.yield.toFixed(2)), bar.week])).toEqual([
      [0.5, 0],
      [0.7, null],
      [0.9, 1],
      [0.55, null],
      [0.2, 2],
    ]);
  });

  it("gives 45 bars for the planner's 12 weeks", () => {
    const twelve: PlantingPlan = {
      ...plan,
      weeks: Array.from({ length: 12 }, (_, index) => ({
        sowing_date: `2026-11-${String(index + 2).padStart(2, "0")}`,
        weather_until: "",
        oni: 2,
        oni_latest_published: false,
        outlooks: [outlook("maize", 0.8, 1)],
      })),
    };
    expect(smoothBars(weekStrip(twelve, "maize"))).toHaveLength(45);
  });
});

describe("stripCrops", () => {
  it("shows the farmer's own crops, the others behind the toggle", () => {
    expect(stripCrops(plan, ["maize", "potato"])).toEqual({
      mine: ["maize"],
      others: ["soybean", "cotton"],
    });
  });

  it("shows the recommended three when the farmer chose none", () => {
    expect(stripCrops(plan, [])).toEqual({ mine: ["soybean", "maize", "cotton"], others: [] });
  });
});
