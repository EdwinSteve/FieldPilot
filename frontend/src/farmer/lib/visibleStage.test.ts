import { describe, expect, it } from "vitest";
import { visibleStage } from "./visibleStage";

const MAIZE = [
  "sowing",
  "germination_emergence",
  "vegetative",
  "flowering",
  "grain_fill",
  "maturity_harvest",
];
const open = (name: string) => ({ name, ended_at: null });
const closed = (name: string) => ({ name, ended_at: "2026-10-05T00:00:00Z" });

describe("visibleStage", () => {
  it("hides with no stage recorded, as the demo seed has", () => {
    expect(visibleStage(MAIZE, [], 33)).toBeNull();
  });

  it("hides sowing on a crop too old for it", () => {
    expect(visibleStage(MAIZE, [open("sowing")], 33)).toBeNull();
  });

  it("shows sowing on a young crop", () => {
    expect(visibleStage(MAIZE, [open("sowing")], 3)?.current).toBe("sowing");
  });

  it("shows the current stage and the next", () => {
    const stage = visibleStage(
      MAIZE,
      [closed("sowing"), closed("germination_emergence"), open("vegetative")],
      33,
    );
    expect(stage).toEqual({
      steps: ["done", "done", "current", "todo", "todo", "todo"],
      current: "vegetative",
      next: "flowering",
    });
  });

  it("follows the order of any crop", () => {
    const beans = ["sowing", "leaves", "pods"];
    expect(visibleStage(beans, [closed("sowing"), open("leaves")], 20)).toEqual({
      steps: ["done", "current", "todo"],
      current: "leaves",
      next: "pods",
    });
  });

  it("has no next stage at the end", () => {
    expect(visibleStage(MAIZE, [open("maturity_harvest")], 120)?.next).toBeNull();
  });
});
