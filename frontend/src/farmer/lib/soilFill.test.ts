import { describe, expect, it } from "vitest";
import { dropFillY, moistureBarScale, soilFill } from "./soilFill";

describe("soilFill", () => {
  it("is the share of field capacity", () => {
    expect(soilFill(20, 32)).toBe(0.625);
  });

  it("stays between empty and full", () => {
    expect(soilFill(-3, 32)).toBe(0);
    expect(soilFill(40, 32)).toBe(1);
  });

  it("reads an impossible capacity as empty", () => {
    expect(soilFill(20, 0)).toBe(0);
  });
});

describe("dropFillY", () => {
  it("spans the drop from its bottom to its tip", () => {
    expect(dropFillY(0)).toBe(20);
    expect(dropFillY(1)).toBe(3);
    expect(dropFillY(0.625)).toBeCloseTo(9.375);
  });
});

describe("moistureBarScale", () => {
  it("matches the design at 20 of 32", () => {
    expect(moistureBarScale(20, 32)).toEqual({ valuePct: 50, fullPct: 80 });
  });

  it("keeps the value on the bar", () => {
    expect(moistureBarScale(90, 32).valuePct).toBe(100);
    expect(moistureBarScale(-1, 32).valuePct).toBe(0);
  });

  it("reads an impossible capacity as empty", () => {
    expect(moistureBarScale(20, 0)).toEqual({ valuePct: 0, fullPct: 0 });
  });
});
