import { describe, expect, it } from "vitest";
import { daysSinceSowing, stageProgress } from "./stages";

describe("stageProgress", () => {
  it("marks the open stage current, past ones done, the rest todo", () => {
    const steps = stageProgress([
      { name: "sowing", ended_at: "2026-10-21T11:00:00Z" },
      { name: "germination_emergence", ended_at: null },
    ]);
    expect(steps.map((s) => s.state)).toEqual(["done", "current", "todo", "todo", "todo", "todo"]);
    expect(steps[0]?.name).toBe("sowing");
  });

  it("reads an unsown crop as all todo and a finished one as all done", () => {
    expect(stageProgress([]).every((s) => s.state === "todo")).toBe(true);
    const done = stageProgress([
      { name: "sowing", ended_at: "2026-10-21T11:00:00Z" },
      { name: "germination_emergence", ended_at: "2026-10-25T11:00:00Z" },
      { name: "vegetative", ended_at: "2026-11-20T11:00:00Z" },
      { name: "flowering", ended_at: "2026-12-10T11:00:00Z" },
      { name: "grain_fill", ended_at: "2027-01-10T11:00:00Z" },
      { name: "maturity_harvest", ended_at: "2027-01-20T11:00:00Z" },
    ]);
    expect(done.every((s) => s.state === "done")).toBe(true);
  });
});

describe("daysSinceSowing", () => {
  it("counts whole plot-local days", () => {
    expect(daysSinceSowing("2026-10-20", "2026-10-20T14:00:00Z", -5)).toBe(0);
    expect(daysSinceSowing("2026-10-20", "2026-10-28T11:00:00Z", -5)).toBe(8);
  });

  it("uses the plot's midnight, not the browser's", () => {
    // 02:00 UTC is still Oct 20 in Neiva.
    expect(daysSinceSowing("2026-10-20", "2026-10-21T02:00:00Z", -5)).toBe(0);
  });

  it("never goes negative and survives bad input", () => {
    expect(daysSinceSowing("2026-10-28", "2026-10-20T11:00:00Z", -5)).toBe(0);
    expect(daysSinceSowing("no-date", "2026-10-20T11:00:00Z", -5)).toBe(0);
  });
});
