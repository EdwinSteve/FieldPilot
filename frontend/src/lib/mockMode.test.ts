import { describe, expect, it } from "vitest";
import type { Report } from "../types/api";
import { ApiError } from "../api/client";
import { dayAlreadyReplayed, isFixtureExhausted, isMockModeChatError } from "./mockMode";

describe("isMockModeChatError", () => {
  it("matches the mock-mode 503 only", () => {
    expect(isMockModeChatError(new ApiError(503, "ChatUnavailableError", "mock"))).toBe(true);
  });

  it("lets every other failure through as a plain error", () => {
    expect(isMockModeChatError(new ApiError(503, "LLMUnavailableError", "down"))).toBe(false);
    expect(isMockModeChatError(new ApiError(422, "ChatUnavailableError", "odd"))).toBe(false);
    expect(isMockModeChatError(new Error("boom"))).toBe(false);
    expect(isMockModeChatError("boom")).toBe(false);
  });
});

describe("isFixtureExhausted", () => {
  it("matches the exhausted-fixture 503 only", () => {
    expect(isFixtureExhausted(new ApiError(503, "FixtureExhaustedError", "mock"))).toBe(true);
  });

  it("lets every other failure through as a plain error", () => {
    expect(isFixtureExhausted(new ApiError(503, "ChatUnavailableError", "mock"))).toBe(false);
    expect(isFixtureExhausted(new ApiError(422, "FixtureExhaustedError", "odd"))).toBe(false);
    expect(isFixtureExhausted(new Error("boom"))).toBe(false);
  });
});

function report(createdAt: string): Report {
  return { id: 1, cycle_id: 1, language: "es", content: "", created_at: createdAt };
}

describe("dayAlreadyReplayed (D076)", () => {
  it("is true when today's local day already has a report", () => {
    expect(dayAlreadyReplayed([report("2026-11-02T11:20:00Z")], "2026-11-02T11:00:00Z", -5)).toBe(true);
  });

  it("is false the next local day, so day 2 can run", () => {
    expect(dayAlreadyReplayed([report("2026-11-02T11:20:00Z")], "2026-11-03T11:00:00Z", -5)).toBe(false);
  });

  it("uses the plot's day, not the UTC day", () => {
    // 03:00 UTC on 3 Nov is still 2 Nov, 22:00 in Neiva.
    expect(dayAlreadyReplayed([report("2026-11-02T11:20:00Z")], "2026-11-03T03:00:00Z", -5)).toBe(true);
  });

  it("is false with no reports", () => {
    expect(dayAlreadyReplayed([], "2026-11-02T11:00:00Z", -5)).toBe(false);
  });
});
