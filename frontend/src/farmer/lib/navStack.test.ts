import { describe, expect, it } from "vitest";
import { backOf, nextStack } from "./navStack";
import type { Route } from "./route";

const TODAY: Route = { screen: "today" };
const UPDATES: Route = { screen: "updates" };
const PLAN: Route = { screen: "plan" };
const DECIDE: Route = { screen: "decide", taskId: 3 };
const REPORT: Route = { screen: "report", reportId: 2 };

function walk(...routes: Route[]): Route[] {
  return routes.reduce<Route[]>((stack, route) => nextStack(stack, route), []);
}

describe("nextStack", () => {
  it("starts a new path at every tab", () => {
    expect(walk(TODAY, PLAN, UPDATES)).toEqual([UPDATES]);
  });

  it("steps forward through screens below a tab", () => {
    expect(walk(UPDATES, PLAN, DECIDE)).toEqual([UPDATES, PLAN, DECIDE]);
  });

  it("treats a return to the screen before as a step back", () => {
    expect(walk(UPDATES, PLAN, DECIDE, PLAN)).toEqual([UPDATES, PLAN]);
  });

  it("ignores a repeat of the same screen", () => {
    expect(walk(TODAY, PLAN, PLAN)).toEqual([TODAY, PLAN]);
  });

  it("tells two tasks apart", () => {
    expect(walk(TODAY, DECIDE, { screen: "decide", taskId: 4 })).toHaveLength(3);
  });

  it("forgets the oldest steps on a very long path", () => {
    const zones = Array.from({ length: 30 }, (_, index): Route => ({
      screen: "zone",
      zoneId: index + 1,
    }));
    expect(walk(TODAY, ...zones)).toHaveLength(20);
  });
});

describe("backOf", () => {
  it("opens the screen the farmer came from", () => {
    expect(backOf(walk(UPDATES, PLAN))).toEqual(UPDATES);
    expect(backOf(walk(UPDATES, PLAN, DECIDE))).toEqual(PLAN);
  });

  it("falls back to the screen's own tab after a reload", () => {
    expect(backOf(walk(REPORT))).toEqual(UPDATES);
    expect(backOf(walk(PLAN))).toEqual(TODAY);
  });

  it("never goes back to Welcome", () => {
    expect(backOf(walk({ screen: "welcome" }, PLAN))).toEqual(TODAY);
  });
});
