import { describe, expect, it } from "vitest";
import { plantsLevel, soilLevel, worstLevel } from "./statusLevel";

describe("soilLevel", () => {
  it.each([
    ["very_dry", "bad"],
    ["dry", "watch"],
    ["ok", "good"],
    ["wet", "watch"],
  ] as const)("reads %s as %s", (status, level) => {
    expect(soilLevel(status)).toBe(level);
  });
});

describe("plantsLevel", () => {
  it("warns on weak plants and judges nothing without a photo", () => {
    expect(plantsLevel(true)).toBe("watch");
    expect(plantsLevel(false)).toBe("good");
    expect(plantsLevel(null)).toBe("neutral");
  });
});

describe("worstLevel", () => {
  it("takes the most serious level", () => {
    expect(worstLevel(["good", "watch"])).toBe("watch");
    expect(worstLevel(["watch", "bad", "good"])).toBe("bad");
    expect(worstLevel(["good", "good"])).toBe("good");
  });

  it("ignores levels that judge nothing", () => {
    expect(worstLevel(["info", "neutral"])).toBe("neutral");
    expect(worstLevel(["info", "good"])).toBe("good");
    expect(worstLevel([])).toBe("neutral");
  });
});
