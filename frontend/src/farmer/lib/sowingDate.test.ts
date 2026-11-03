import { describe, expect, it } from "vitest";
import { earliestSowing, plotToday, sowingDateProblem } from "./sowingDate";

describe("the sowing date", () => {
  it("takes today from the plot's clock", () => {
    expect(plotToday("2026-11-03T03:00:00Z", -5)).toBe("2026-11-02");
  });

  it("goes back 60 days at most", () => {
    expect(earliestSowing("2026-11-02")).toBe("2026-09-03");
  });

  it("accepts today and the last 60 days only", () => {
    expect(sowingDateProblem("2026-11-02", "2026-11-02")).toBeNull();
    expect(sowingDateProblem("2026-09-03", "2026-11-02")).toBeNull();
    expect(sowingDateProblem("2026-11-03", "2026-11-02")).toBe("future");
    expect(sowingDateProblem("2026-09-02", "2026-11-02")).toBe("too_old");
    expect(sowingDateProblem("", "2026-11-02")).toBe("missing");
  });
});
