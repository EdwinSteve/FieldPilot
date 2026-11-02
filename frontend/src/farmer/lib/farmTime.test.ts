import { describe, expect, it } from "vitest";
import {
  daysFromToday,
  formatCalendarDate,
  formatClock,
  formatClockRange,
  formatDateLine,
  localHour,
  plusDays,
  relativeDay,
  shortWeekday,
} from "./farmTime";

const OFFSET = -5;
const MONDAY_6AM = "2026-11-02T11:00:00Z";

describe("clock times", () => {
  it("reads the plot's local time", () => {
    expect(formatClock(MONDAY_6AM, OFFSET)).toBe("6:00 am");
    expect(localHour(MONDAY_6AM, OFFSET)).toBe(6);
  });

  it("handles noon and midnight", () => {
    expect(formatClock("2026-11-02T17:05:00Z", OFFSET)).toBe("12:05 pm");
    expect(formatClock("2026-11-02T05:00:00Z", OFFSET)).toBe("12:00 am");
  });

  it("keeps one am or pm inside a range", () => {
    expect(formatClockRange("2026-11-03T11:00:00Z", "2026-11-03T14:20:00Z", OFFSET)).toBe(
      "6:00–9:20 am",
    );
    expect(formatClockRange("2026-11-03T16:00:00Z", "2026-11-03T19:20:00Z", OFFSET)).toBe(
      "11:00 am–2:20 pm",
    );
  });
});

describe("dates", () => {
  it("writes the header line", () => {
    expect(formatDateLine(MONDAY_6AM, OFFSET)).toBe("Monday, 2 Nov · 6:00 am");
  });

  it("uses the plot's day, not UTC's", () => {
    expect(shortWeekday("2026-11-03T02:00:00Z", OFFSET)).toBe("Mon");
  });

  it("writes a calendar date, and leaves a bad one alone", () => {
    expect(formatCalendarDate("2026-10-28")).toBe("28 Oct");
    expect(formatCalendarDate("soon")).toBe("soon");
  });
});

describe("relativeDay", () => {
  it.each([
    ["2026-11-02T11:00:00Z", "Today"],
    ["2026-11-01T11:00:00Z", "Yesterday"],
    ["2026-11-03T11:00:00Z", "Tomorrow"],
    ["2026-11-04T11:00:00Z", "Wed"],
  ])("reads %s as %s", (iso, label) => {
    expect(relativeDay(iso, MONDAY_6AM, OFFSET)).toBe(label);
  });

  it("counts plot days", () => {
    expect(daysFromToday("2026-11-04T11:00:00Z", MONDAY_6AM, OFFSET)).toBe(2);
  });
});

describe("plusDays", () => {
  it("moves whole days", () => {
    expect(plusDays(MONDAY_6AM, 1)).toBe("2026-11-03T11:00:00.000Z");
  });
});
