import { describe, expect, it } from "vitest";
import { SITE_STEPS, siteStep } from "./siteSteps";

describe("siteStep", () => {
  it("moves on every 30 seconds", () => {
    expect(siteStep(0)).toBe(0);
    expect(siteStep(29_999)).toBe(0);
    expect(siteStep(30_000)).toBe(1);
    expect(siteStep(65_000)).toBe(2);
  });

  it("waits on the last step however long it takes", () => {
    expect(siteStep(90_000)).toBe(SITE_STEPS.length - 1);
    expect(siteStep(600_000)).toBe(SITE_STEPS.length - 1);
  });

  it("starts at the first step for a clock that went back", () => {
    expect(siteStep(-5_000)).toBe(0);
  });
});
