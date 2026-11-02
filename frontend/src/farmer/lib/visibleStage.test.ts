import { describe, expect, it } from "vitest";
import { visibleStage } from "./visibleStage";

const open = (name: string) => ({ name, ended_at: null });
const closed = (name: string) => ({ name, ended_at: "2026-10-05T00:00:00Z" });

describe("visibleStage", () => {
  it("hides with no stage recorded, as the demo seed has", () => {
    expect(visibleStage([], 33)).toBeNull();
  });

  it("hides sowing on a crop too old for it", () => {
    expect(visibleStage([open("sowing")], 33)).toBeNull();
  });

  it("shows sowing on a young crop", () => {
    expect(visibleStage([open("sowing")], 3)?.current).toBe("sowing");
  });

  it("shows the current stage and the next", () => {
    const stage = visibleStage(
      [closed("sowing"), closed("germination_emergence"), open("vegetative")],
      33,
    );
    expect(stage).toEqual({
      steps: ["done", "done", "current", "todo", "todo", "todo"],
      current: "vegetative",
      next: "flowering",
    });
  });

  it("has no next stage at the end", () => {
    expect(visibleStage([open("maturity_harvest")], 120)?.next).toBeNull();
  });
});
