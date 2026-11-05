import { describe, expect, it } from "vitest";
import { percentFull, soilTrend } from "./soilTrend";

const MONDAY = "2026-11-02T11:00:00Z";
const TUESDAY = "2026-11-03T11:00:00Z";
const reading = (value: number, recorded_at: string) => ({ value, recorded_at });

describe("soilTrend", () => {
  it("is down when the soil dried since yesterday", () => {
    expect(soilTrend([reading(20, MONDAY), reading(16.7, TUESDAY)], TUESDAY)).toEqual({
      direction: "down",
      previous: 20,
    });
  });

  it("is up after watering", () => {
    expect(soilTrend([reading(16.7, MONDAY), reading(22, TUESDAY)], TUESDAY)?.direction).toBe("up");
  });

  it("is steady for a change too small to mean anything", () => {
    expect(soilTrend([reading(20, MONDAY), reading(20.3, TUESDAY)], TUESDAY)?.direction).toBe(
      "steady",
    );
  });

  it("needs a reading from about a day before", () => {
    expect(soilTrend([reading(20, MONDAY)], MONDAY)).toBeNull();
    expect(soilTrend([reading(20, MONDAY), reading(19, "2026-11-02T20:00:00Z")], TUESDAY)).toBeNull();
    expect(soilTrend([], MONDAY)).toBeNull();
  });

  it("ignores readings after the simulated now", () => {
    expect(soilTrend([reading(20, MONDAY), reading(16.7, TUESDAY)], MONDAY)).toBeNull();
  });
});

describe("percentFull", () => {
  it("is the share of what the soil can hold", () => {
    expect(percentFull(20, 32)).toBe(63);
    expect(percentFull(16.7, 32)).toBe(52);
  });

  it("stops at full", () => {
    expect(percentFull(40, 32)).toBe(100);
  });
});
