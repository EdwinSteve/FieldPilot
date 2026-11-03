import { describe, expect, it } from "vitest";
import { gatedRoute, startRoute } from "./accountGate";
import type { Route } from "./route";

const PLAN: Route = { screen: "plan" };

describe("startRoute", () => {
  it("opens the farm, the log-in or a first account", () => {
    expect(startRoute(true, true)).toEqual({ screen: "today" });
    expect(startRoute(false, true)).toEqual({ screen: "login" });
    expect(startRoute(false, false)).toEqual({ screen: "signup" });
  });
});

describe("gatedRoute", () => {
  it("shows any screen once signed in", () => {
    expect(gatedRoute(PLAN, true, true)).toEqual(PLAN);
    expect(gatedRoute({ screen: "signup" }, true, true)).toEqual({ screen: "signup" });
  });

  it("skips the log-in for a farmer already signed in", () => {
    expect(gatedRoute({ screen: "login" }, true, true)).toEqual({ screen: "today" });
  });

  it("puts the log-in, or a first account, in front of farm screens", () => {
    expect(gatedRoute(PLAN, false, true)).toEqual({ screen: "login" });
    expect(gatedRoute(PLAN, false, false)).toEqual({ screen: "signup" });
  });

  it("lets Welcome and the account screens open signed out", () => {
    expect(gatedRoute({ screen: "welcome" }, false, false)).toEqual({ screen: "welcome" });
    expect(gatedRoute({ screen: "login" }, false, true)).toEqual({ screen: "login" });
  });
});
