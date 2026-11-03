import { describe, expect, it } from "vitest";
import { gatedRoute, homeRoute, startRoute } from "./accountGate";
import type { Route } from "./route";

const PLAN: Route = { screen: "plan" };

describe("startRoute", () => {
  it("opens the farm, the log-in or a first account", () => {
    expect(startRoute(true, true)).toEqual({ screen: "today" });
    expect(startRoute(false, true)).toEqual({ screen: "login" });
    expect(startRoute(false, false)).toEqual({ screen: "signup" });
  });
});

describe("homeRoute", () => {
  it("sets up the farm, then chooses what to sow, then farms", () => {
    expect(homeRoute("no_plot")).toEqual({ screen: "setup" });
    expect(homeRoute("no_cycle")).toEqual({ screen: "advice" });
    expect(homeRoute("farming")).toEqual({ screen: "today" });
  });
});

describe("gatedRoute signed out", () => {
  it("puts the log-in, or a first account, in front of farm and setup screens", () => {
    expect(gatedRoute(PLAN, false, true, "loading")).toEqual({ screen: "login" });
    expect(gatedRoute({ screen: "setup" }, false, false, "loading")).toEqual({ screen: "signup" });
  });

  it("lets Welcome and the account screens open", () => {
    expect(gatedRoute({ screen: "welcome" }, false, false, "loading")).toEqual({ screen: "welcome" });
    expect(gatedRoute({ screen: "login" }, false, true, "loading")).toEqual({ screen: "login" });
  });
});

describe("gatedRoute signed in", () => {
  it("keeps the screen asked for while the farm loads", () => {
    expect(gatedRoute(PLAN, true, true, "loading")).toEqual(PLAN);
  });

  it("sends a farmer without a farm to set one up, whatever was asked", () => {
    expect(gatedRoute(PLAN, true, true, "no_plot")).toEqual({ screen: "setup" });
    expect(gatedRoute({ screen: "signup" }, true, true, "no_plot")).toEqual({ screen: "setup" });
  });

  it("opens Settings once the farm exists, sown or not", () => {
    const settings: Route = { screen: "settings" };
    expect(gatedRoute(settings, true, true, "no_cycle")).toEqual(settings);
    expect(gatedRoute(settings, true, true, "farming")).toEqual(settings);
    expect(gatedRoute(settings, true, true, "no_plot")).toEqual({ screen: "setup" });
    expect(gatedRoute(settings, false, true, "farming")).toEqual({ screen: "login" });
  });

  it("sends a farm not yet sown to choose what to sow", () => {
    expect(gatedRoute({ screen: "setup" }, true, true, "no_cycle")).toEqual({ screen: "advice" });
  });

  it("shows any farm screen once a crop grows, and setup is done", () => {
    expect(gatedRoute(PLAN, true, true, "farming")).toEqual(PLAN);
    expect(gatedRoute({ screen: "advice" }, true, true, "farming")).toEqual({ screen: "today" });
    expect(gatedRoute({ screen: "login" }, true, true, "farming")).toEqual({ screen: "today" });
  });

  it("still lets Welcome open", () => {
    expect(gatedRoute({ screen: "welcome" }, true, true, "farming")).toEqual({ screen: "welcome" });
  });
});
