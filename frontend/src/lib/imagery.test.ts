import { describe, expect, it } from "vitest";
import { boxRect, ndviPosition } from "./imagery";

describe("boxRect", () => {
  it("reads x, y, width and height from a normalized box", () => {
    expect(boxRect({ x1: 0.5, y1: 0.0, x2: 1.0, y2: 1.0 })).toEqual({
      x: 0.5,
      y: 0.0,
      width: 0.5,
      height: 1.0,
    });
  });
});

describe("ndviPosition", () => {
  it("maps the NDVI range onto 0-100", () => {
    expect(ndviPosition(-1)).toBe(0);
    expect(ndviPosition(0)).toBe(50);
    expect(ndviPosition(1)).toBe(100);
    expect(ndviPosition(0.378)).toBeCloseTo(68.9, 1);
  });

  it("clamps outliers and keeps nulls", () => {
    expect(ndviPosition(2)).toBe(100);
    expect(ndviPosition(-2)).toBe(0);
    expect(ndviPosition(null)).toBeNull();
  });
});
