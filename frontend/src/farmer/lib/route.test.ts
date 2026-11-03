import { describe, expect, it } from "vitest";
import { hrefOf, isEntryScreen, isSetupScreen, parseRoute, tabOf, type Route } from "./route";

describe("parseRoute", () => {
  it("opens on Welcome with no hash", () => {
    expect(parseRoute("")).toEqual({ screen: "welcome" });
    expect(parseRoute("#/")).toEqual({ screen: "welcome" });
  });

  it("reads plain screens and screens with an id", () => {
    expect(parseRoute("#/plan")).toEqual({ screen: "plan" });
    expect(parseRoute("#/login")).toEqual({ screen: "login" });
    expect(parseRoute("#/signup")).toEqual({ screen: "signup" });
    expect(parseRoute("#/decide/3")).toEqual({ screen: "decide", taskId: 3 });
    expect(parseRoute("#/zone/1")).toEqual({ screen: "zone", zoneId: 1 });
    expect(parseRoute("#/report/2")).toEqual({ screen: "report", reportId: 2 });
  });

  it.each(["#/nothing", "#/decide", "#/decide/x", "#/decide/-1", "#/today/2", "#/zone/1/2"])(
    "falls back to Today on %s",
    (hash) => {
      expect(parseRoute(hash)).toEqual({ screen: "today" });
    },
  );
});

describe("hrefOf", () => {
  it.each<[Route]>([
    [{ screen: "today" }],
    [{ screen: "stop" }],
    [{ screen: "settings" }],
    [{ screen: "decide", taskId: 7 }],
    [{ screen: "zone", zoneId: 1 }],
    [{ screen: "report", reportId: 2 }],
  ])("round-trips %j", (route) => {
    expect(parseRoute(hrefOf(route))).toEqual(route);
  });
});

describe("isEntryScreen", () => {
  it("lets Welcome and the account screens open signed out", () => {
    expect(isEntryScreen({ screen: "welcome" })).toBe(true);
    expect(isEntryScreen({ screen: "login" })).toBe(true);
    expect(isEntryScreen({ screen: "signup" })).toBe(true);
    expect(isEntryScreen({ screen: "today" })).toBe(false);
  });
});

describe("isSetupScreen", () => {
  it("marks setting up the farm and choosing what to sow", () => {
    expect(parseRoute("#/setup")).toEqual({ screen: "setup" });
    expect(parseRoute("#/advice")).toEqual({ screen: "advice" });
    expect(isSetupScreen({ screen: "advice" })).toBe(true);
    expect(isSetupScreen({ screen: "plan" })).toBe(false);
    expect(tabOf({ screen: "setup" })).toBeNull();
  });
});

describe("tabOf", () => {
  it("marks the tab the design marks", () => {
    expect(tabOf({ screen: "welcome" })).toBeNull();
    expect(tabOf({ screen: "login" })).toBeNull();
    expect(tabOf({ screen: "decide", taskId: 1 })).toBe("today");
    expect(tabOf({ screen: "report", reportId: 1 })).toBe("updates");
    expect(tabOf({ screen: "talk" })).toBe("talk");
  });
});
