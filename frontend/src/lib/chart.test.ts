import { describe, expect, it } from "vitest";
import { seriesRange, toPoints } from "./chart";

describe("seriesRange", () => {
  it("pads the extremes by a tenth", () => {
    expect(seriesRange([10, 20])).toEqual({ min: 9, max: 21 });
  });

  it("gives a flat line room", () => {
    expect(seriesRange([15, 15])).toEqual({ min: 13.5, max: 16.5 });
  });

  it("reads nothing from nothing", () => {
    expect(seriesRange([])).toBeNull();
  });
});

describe("toPoints", () => {
  it("spreads values across the box, higher values higher up", () => {
    expect(toPoints([0, 10], 100, 40, { min: 0, max: 10 })).toBe("0,40 100,0");
  });

  it("centres a single value", () => {
    expect(toPoints([5], 100, 40, { min: 0, max: 10 })).toBe("50,20");
  });
});
