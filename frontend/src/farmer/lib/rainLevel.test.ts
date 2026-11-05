import { describe, expect, it } from "vitest";
import { rainDrops, rainLevel } from "./rainLevel";

describe("rainLevel", () => {
  it.each([
    [0, "none"],
    [-1, "none"],
    [Number.NaN, "none"],
    [0.1, "light"],
    [4.9, "light"],
    [5, "some"],
    [12, "some"],
    [20, "some"],
    [20.1, "heavy"],
  ])("reads %s mm as %s", (mm, level) => {
    expect(rainLevel(mm)).toBe(level);
  });
});

describe("rainDrops", () => {
  it("shows 0 to 3 drops", () => {
    expect([rainDrops("none"), rainDrops("light"), rainDrops("some"), rainDrops("heavy")]).toEqual([
      0, 1, 2, 3,
    ]);
  });
});
