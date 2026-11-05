// The agronomist's work in the farmer app (D093), the forecast (D095) and the badge (D094).
import { describe, expect, it } from "vitest";
import type { Task, Weather } from "../../types/api";
import { demo } from "../fixtures/snapshots";
import { decisionView } from "./decide";
import { rainNext24h, rainOnDay, type FarmSnapshot } from "./snapshot";
import { todayView } from "./today";
import { updatesView } from "./updates";

const base = demo.day1Held;
const NOW = base.clock.now;
const ZONE = base.zone?.id ?? null;

function task(overrides: Partial<Task>): Task {
  const template = base.tasks[0];
  if (template === undefined) throw new Error("the fixture has a task");
  return {
    ...template,
    id: 50,
    action_type: "fertilizer",
    zone_id: ZONE,
    params: { product: "urea", dose_kg_ha: 100 },
    rationale: "Zone 2 is short of nitrogen and no rain is coming.",
    status: "pending_approval",
    scheduled_for: NOW,
    created_at: NOW,
    updated_at: NOW,
    revert_open: null,
    ...overrides,
  };
}

function withTasks(...tasks: Task[]): FarmSnapshot {
  return { ...base, tasks };
}

function weather(next24h: number | null, hours: [string, number][]): Weather {
  return {
    plot_id: base.plot.id,
    source: "open_meteo_fixture",
    latitude: 2.95,
    longitude: -75.3,
    as_of: NOW,
    rain_next_24h_mm: next24h,
    hours: hours.map(([hour_ending, rain_mm]) => ({ hour_ending, rain_mm })),
  };
}

describe("the forecast (D095)", () => {
  it("comes from the weather endpoint, not from a gate verdict", () => {
    const farm: FarmSnapshot = { ...base, verdicts: [], weather: weather(7.25, []) };

    expect(rainNext24h(farm)).toBe(7.3);
    expect(todayView(farm).rain).toMatchObject({ known: true, mm: 7.3 });
  });

  it("falls back to today's gate verdict without the endpoint", () => {
    expect(rainNext24h({ ...base, weather: null })).toBe(rainNext24h(base));
    expect(todayView({ ...base, verdicts: [], weather: null }).rain.known).toBe(false);
  });

  it("marks rain on tomorrow's day of the week strip", () => {
    const tomorrow = new Date(Date.parse(NOW) + 26 * 3_600_000).toISOString();
    const farm: FarmSnapshot = { ...base, weather: weather(0, [[tomorrow, 4]]) };

    expect(rainOnDay(farm, tomorrow)).toBe(4);
    const week = todayView(farm).week;
    const today = week.findIndex((day) => day.today);
    expect(week[today + 1]?.rain).toBe(true); // the fixture's day is a Monday
    expect(week[today]?.rain).toBe(false);
  });
});

describe("the agronomist's field work (D093)", () => {
  it("asks for a fertilizer with what, when and why, not soil and water", () => {
    const view = decisionView(withTasks(task({})), 50);

    expect(view?.question).toBe("Fertilizer · Zone 2?");
    expect(view?.work).toMatchObject({
      title: "Fertilizer · Zone 2",
      dose: "urea, 100 kg/ha",
      rationale: "Zone 2 is short of nitrogen and no rain is coming.",
    });
    expect(view?.why).toMatch(/always wait for you/);
    expect(todayView(withTasks(task({}))).decision?.question).toBe("Fertilizer · Zone 2?");
  });

  it("lists an approved task on Today until the farmer taps Done", () => {
    const approved = task({ status: "scheduled" });
    const visit = task({ id: 51, action_type: "scouting_visit", params: {}, status: "scheduled" });

    const items = todayView(withTasks(approved, visit)).fieldWork;

    expect(items.map((item) => item.title)).toEqual([
      "Fertilizer · Zone 2",
      "Look at the plants · Zone 2",
    ]);
    expect(items[0]?.detail).toMatch(/^urea, 100 kg\/ha · Today/);
    expect(todayView(withTasks(task({ status: "executed" }))).fieldWork).toEqual([]);
  });

  it("tells done and withdrawn tasks in Updates", () => {
    const titles = updatesView(
      withTasks(task({ status: "executed" }), task({ id: 52, status: "cancelled" })),
    ).items.map((item) => item.title);

    expect(titles).toContain("Done: Fertilizer · Zone 2");
    expect(titles).toContain("FieldPilot withdrew: Fertilizer · Zone 2");
  });
});

describe("the LIVE/REPLAY badge (D094)", () => {
  it("says replay with the recording's date, or live with the model", () => {
    const replay = todayView({
      ...base,
      health: {
        status: "ok",
        mock_llm: true,
        llm_mode: "replay",
        agent_model: null,
        replay: { recorded_on: "2026-11-04", model: "muse-spark-1.3" },
      },
    }).mode;
    const live = todayView({
      ...base,
      health: { status: "ok", mock_llm: false, llm_mode: "live", agent_model: "muse-spark-1.3" },
    }).mode;

    expect(replay).toMatchObject({ live: false, text: "REPLAY · recorded 2026-11-04" });
    expect(live).toMatchObject({ live: true, text: "LIVE · Muse Spark (muse-spark-1.3)" });
    expect(todayView(base).mode).toBeNull();
  });
});
