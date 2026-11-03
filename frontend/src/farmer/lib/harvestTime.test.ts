import { describe, expect, it } from "vitest";
import { harvestTiming, type CropGrowth } from "./harvestTime";

const STAGES = ["sowing", "vegetative", "flowering", "maturity_harvest"];
const growth: CropGrowth = {
  currentStage: "flowering",
  stageOrder: STAGES,
  accumulatedGdd: 1000,
  maturityGdd: 1500,
  daysSinceSowing: 100,
};

describe("harvestTiming", () => {
  it("is ready in the last stage or at the maturity heat", () => {
    expect(harvestTiming({ ...growth, currentStage: "maturity_harvest" })).toEqual({ kind: "ready" });
    expect(harvestTiming({ ...growth, accumulatedGdd: 1500 })).toEqual({ kind: "ready" });
  });

  it("counts the days left at the pace so far", () => {
    // 10 GDD a day, 500 to go: 50 days, so not soon.
    expect(harvestTiming(growth)).toEqual({ kind: "later" });
    // 1400 in 100 days is 14 a day, 100 to go: 8 days.
    expect(harvestTiming({ ...growth, accumulatedGdd: 1400 })).toEqual({ kind: "soon", days: 8 });
  });

  it("calls 14 days soon and 15 later", () => {
    // 10 a day; 140 to go is 14 days, 150 is 15.
    expect(harvestTiming({ ...growth, accumulatedGdd: 1360, daysSinceSowing: 136 })).toEqual({
      kind: "soon",
      days: 14,
    });
    expect(harvestTiming({ ...growth, accumulatedGdd: 1350, daysSinceSowing: 135 })).toEqual({
      kind: "later",
    });
  });

  it("promises nothing without a catalogue or before the crop has grown", () => {
    expect(harvestTiming({ ...growth, maturityGdd: null, stageOrder: [] })).toEqual({ kind: "unknown" });
    expect(harvestTiming({ ...growth, accumulatedGdd: 0 })).toEqual({ kind: "unknown" });
    expect(harvestTiming({ ...growth, daysSinceSowing: 0 })).toEqual({ kind: "unknown" });
  });
});
