import { describe, expect, it } from "vitest";
import { formatDayMonth, formatDuration, formatNumber, formatPlotTime, plotDay } from "./format";

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

describe("formatDayMonth", () => {
  it("reads the day and short month", () => {
    expect(formatDayMonth("2026-10-20")).toBe("20 oct");
    expect(formatDayMonth("2026-01-05")).toBe("5 ene");
  });

  it("leaves bad input alone", () => {
    expect(formatDayMonth("no-date")).toBe("no-date");
  });
});

describe("plotDay", () => {
  it("is the plot's local calendar day", () => {
    expect(plotDay("2026-11-02T11:00:00Z", -5)).toBe("2026-11-02");
    expect(plotDay("2026-11-03T03:00:00Z", -5)).toBe("2026-11-02");
  });
});
