import { describe, expect, it } from "vitest";
import { pointsToFull, roundReading, soilStatus } from "./soilStatus";

describe("soilStatus", () => {
  it.each([
    [16.7, "very_dry"],
    [17.6, "dry"],
    [20, "dry"],
    [22.4, "ok"],
    [31.9, "ok"],
    [32, "wet"],
  ])("reads %s of 32 as %s", (value, status) => {
    expect(soilStatus(value, 32)).toBe(status);
  });
});

describe("pointsToFull", () => {
  it("rounds what is missing", () => {
    expect(pointsToFull(20, 32)).toBe(12);
    expect(pointsToFull(16.7, 32)).toBe(15);
  });

  it("is never negative", () => {
    expect(pointsToFull(35, 32)).toBe(0);
  });
});

describe("roundReading", () => {
  it("keeps one decimal at most", () => {
    expect(roundReading(16.737354753268832)).toBe(16.7);
    expect(roundReading(20)).toBe(20);
  });
});
