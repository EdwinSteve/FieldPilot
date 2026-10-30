import { describe, expect, it } from "vitest";
import { formatDuration, formatNumber, formatPlotTime } from "./format";

describe("formatDuration", () => {
  it.each([
    [0, "0 s"],
    [45, "45 s"],
    [60, "1 min"],
    [3_900, "1 h 05 min"],
    [21_600, "6 h 00 min"],
    [86_400, "1 d"],
    [97_200, "1 d 3 h"],
  ])("%d s reads as %s", (seconds, text) => {
    expect(formatDuration(seconds)).toBe(text);
  });

  it("treats negative and invalid values as zero", () => {
    expect(formatDuration(-5)).toBe("0 s");
    expect(formatDuration(Number.NaN)).toBe("0 s");
  });
});

describe("formatNumber", () => {
  it("uses a decimal comma, like the backend catalogue", () => {
    expect(formatNumber(20.5)).toBe("20,5");
    expect(formatNumber(0.378, 3)).toBe("0,378");
    expect(formatNumber(15)).toBe("15");
  });
});

describe("formatPlotTime", () => {
  it("shows the plot's local time, not the browser's", () => {
    expect(formatPlotTime("2026-10-28T11:00:00Z", -5)).toBe("28 oct, 06:00");
    expect(formatPlotTime("2026-10-28T03:30:00Z", -5)).toBe("27 oct, 22:30");
  });
});
