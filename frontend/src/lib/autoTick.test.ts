import { describe, expect, it } from "vitest";
import { AUTO_TICK_MS, isTickDue, shouldAutoTick } from "./autoTick";

describe("shouldAutoTick", () => {
  it("ticks while the clock runs and the tab is visible", () => {
    expect(shouldAutoTick(false, false)).toBe(true);
  });

  it("never ticks while the clock is paused", () => {
    expect(shouldAutoTick(true, false)).toBe(false);
  });

  it("never ticks while the tab is hidden", () => {
    expect(shouldAutoTick(false, true)).toBe(false);
    expect(shouldAutoTick(true, true)).toBe(false);
  });
});

describe("AUTO_TICK_MS", () => {
  it("ticks about every 5 s of real time (D070)", () => {
    expect(AUTO_TICK_MS).toBe(5_000);
  });
});

describe("isTickDue", () => {
  it("is due when the last tick is at least 5 s old", () => {
    expect(isTickDue(1_000, 6_000)).toBe(true);
    expect(isTickDue(1_000, 6_001)).toBe(true);
  });

  it("is not due within 5 s of the last tick", () => {
    expect(isTickDue(1_000, 5_999)).toBe(false);
    expect(isTickDue(1_000, 1_000)).toBe(false);
  });

  it("is due when nothing ever ticked", () => {
    expect(isTickDue(0, Date.now())).toBe(true);
  });
});
