import { describe, expect, it } from "vitest";
import { ApiError } from "../api/client";
import { isFixtureExhausted, isMockModeChatError } from "./mockMode";

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
