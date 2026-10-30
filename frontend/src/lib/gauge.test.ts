import { describe, expect, it } from "vitest";
import { arcPath, gaugeFraction, polar } from "./gauge";

describe("polar", () => {
  it("points up at 0° and goes clockwise", () => {
    expect(polar(60, 60, 50, 0)).toEqual({ x: 60, y: 10 });
    expect(polar(60, 60, 50, 90)).toEqual({ x: 110, y: 60 });
    expect(polar(60, 60, 50, 180)).toEqual({ x: 60, y: 110 });
    expect(polar(60, 60, 50, 270)).toEqual({ x: 10, y: 60 });
  });

  it("wraps angles past a full turn", () => {
    expect(polar(0, 0, 10, 450)).toEqual(polar(0, 0, 10, 90));
  });
});

describe("arcPath", () => {
  it("draws a small clockwise arc", () => {
    expect(arcPath(60, 60, 50, 0, 90)).toBe("M 60 10 A 50 50 0 0 1 110 60");
  });

  it("takes the long way past 180°", () => {
    expect(arcPath(60, 60, 50, 0, 200).split(" ")).toContain("1");
  });
});

describe("gaugeFraction", () => {
  it("divides moisture by field capacity", () => {
    expect(gaugeFraction(21, 32)).toBeCloseTo(0.656, 3);
    expect(gaugeFraction(40, 32)).toBeCloseTo(1.25, 3);
  });

  it("never goes negative or divides by nothing", () => {
    expect(gaugeFraction(undefined, 32)).toBe(0);
    expect(gaugeFraction(21, 0)).toBe(0);
    expect(gaugeFraction(-5, 32)).toBe(0);
  });
});
