import { describe, expect, it } from "vitest";
import type { LogEvent } from "../../types/api";
import { demo } from "../fixtures/snapshots";
import type { LookedAt } from "../lib/lookedAt";
import { stopView, talkView } from "./control";
import { decisionView } from "./decide";
import { fieldView } from "./field";
import { planView } from "./plan";
import { reportView } from "./report";
import type { FarmSnapshot } from "./snapshot";
import { todayView } from "./today";
import { updatesView } from "./updates";
import { zoneView } from "./zone";

const ZONE_ID = 1;
const HELD_TASK = 1;
const EXTRA_TASK = 3;

describe("a plot with two zones (D089)", () => {
  const lead = demo.day2Cycle;
  const moist = {
    zone: { id: 99, plot_id: lead.plot.id, name: "Zona 1", area_ha: 0.5, field_capacity_pct: 32 },
    readings: [{ value: 27, recorded_at: lead.clock.now }],
  };
  const farm: FarmSnapshot = { ...lead, zones: [...lead.zones, moist] };

  it("lists the other zone under the status card, with its soil and a way in", () => {
    expect(todayView(farm).otherZones).toEqual([
      { name: "Zone 1", status: "OK", level: "good", display: "27%", href: "#/zone/99" },
    ]);
    expect(todayView(lead).otherZones).toEqual([]);
  });

  it("opens the other zone with its own soil", () => {
    expect(zoneView(farm, 99)?.display).toBe("27%");
    expect(zoneView(farm, 99)?.name).toBe("Zone 1");
  });
});

describe("todayView", () => {
  it("on a farm set up in the app, with no zone yet, says there are no sensors", () => {
    const view = todayView({ ...demo.seed, zone: null, readings: [] });
    expect(view.statusTitle).toBe("No soil sensors on this farm yet");
    expect(view.statusDetail).toContain("Soil readings start once sensors are in.");
    expect(view.soil.display).toBe("—");
  });

  it("before the first cycle: soil only, nothing to decide", () => {
    const view = todayView(demo.seed);
    expect(view.decision).toBeNull();
    expect(view.soil.display).toBe("20");
    expect(view.soil.ofFull).toBe("of 32%");
    expect(view.rain.display).toBe("—");
    expect(view.rain.known).toBe(false);
    // Dry soil and no plan yet: the line says why nothing is watering.
    expect(view.statusDetail).toBe("Today’s check hasn’t run yet, so no watering is planned.");
  });

  it("day 1: asks first, with the demo's numbers", () => {
    const view = todayView(demo.day1Held);
    expect(view.dateLine).toBe("Monday, 2 Nov · 6:00 am");
    expect(view.greeting).toBe("Good morning");
    expect(view.farmLine).toBe("Finca demo · Maize, day 32");
    expect(view.decision).toEqual({ taskId: HELD_TASK, question: "Water Zone 2?" });
    expect(view.statusTitle).toBe("Zone 2 is dry");
    expect(view.statusDetail).toBe("Rain expected in the next 24 h");
    expect(view.soil.label).toBe("Soil · dry");
    expect(view.rain).toEqual({ mm: 12, known: true, display: "12 mm", label: "Rain · some" });
    expect(view.plants.value).toBe("Weak");
    expect(view.week[0]).toEqual({
      day: "Mon",
      today: true,
      water: true,
      rain: true,
      saidNo: false,
    });
    expect(view.stoppedBanner).toBeNull();
    expect(view.status).toBe("watch");
    expect(view.statusLabel).toBe("Keep an eye on this");
    expect(view.soil.trend).toBeNull();
    expect(view.soil.level).toBe("watch");
    expect(view.plants.level).toBe("watch");
  });

  it("judges nothing it cannot read", () => {
    const view = todayView({ ...demo.seed, readings: [], imagery: { scene: null, zones: [], boxes: [] } });
    expect(view.status).toBe("neutral");
    expect(view.soil.level).toBe("neutral");
    expect(view.plants.level).toBe("neutral");
  });

  it("recent updates: newest first, two at most", () => {
    const view = todayView(demo.day2Undone);
    expect(view.recent.map((item) => item.id)).toEqual(["water-2", "cancelled-3"]);
  });

  it("recent updates: an open undo comes first, with its time left", () => {
    const [undo, next, ...rest] = todayView(demo.day2Cycle).recent;
    expect(undo?.title).toBe("Extra water, tomorrow");
    expect(undo?.time).toBe("6 h 00 min left to undo");
    expect(undo?.href).toBe("#/updates");
    expect(next?.id).toBe("water-2");
    expect(rest).toEqual([]);
  });

  it("recent updates: empty before the first cycle", () => {
    expect(todayView(demo.seed).recent).toEqual([]);
  });

  it("a rejected task leaves the week strip, marked as a no", () => {
    const monday = todayView(demo.day1Rejected).week[0];
    expect(monday?.water).toBe(false);
    expect(monday?.saidNo).toBe(true);
  });

  it("a day with a watering is not marked as a no", () => {
    const tuesday = todayView(demo.day2Cycle).week[1];
    expect(tuesday?.water).toBe(true);
    expect(tuesday?.saidNo).toBe(false);
  });

  it("dry soil after today's check, with nothing planned, says when it looks again", () => {
    expect(todayView(demo.day1Rejected).statusDetail).toBe(
      "No watering planned. I will look again tomorrow morning.",
    );
  });

  it("keeps the rain line while a watering waits for the farmer", () => {
    expect(todayView(demo.day1Held).statusDetail).toBe("Rain expected in the next 24 h");
  });

  it("day 2 before the cycle: yesterday's forecast is not shown", () => {
    const view = todayView(demo.day2Morning);
    expect(view.rain.display).toBe("—");
    expect(view.statusTitle).toBe("Zone 2 is very dry");
  });

  it("day 2 after the cycle: nothing to decide, no rain", () => {
    const view = todayView(demo.day2Cycle);
    expect(view.decision).toBeNull();
    expect(view.statusDetail).toBe("No rain expected");
    expect(view.soil.display).toBe("16.7");
    expect(view.soil.label).toBe("Very dry");
    expect(view.status).toBe("bad");
    expect(view.statusLabel).toBe("Problem");
    expect(view.soil.trend).toBe("down");
    expect(view.rain.known).toBe(true);
  });

  it("never claims watering stopped while water still runs", () => {
    const stopped = { ...demo.day2Cycle, stop: { ...demo.day2Cycle.stop, active: true } };
    expect(todayView(stopped).stoppedBanner).toBe("New watering is blocked");
    const dry = { ...demo.day1Held, stop: { ...demo.day1Held.stop, active: true } };
    expect(todayView(dry).stoppedBanner).toBe("Watering is stopped");
  });
});

describe("decisionView", () => {
  it("shows what the gate saw", () => {
    expect(decisionView(demo.day1Held, HELD_TASK)).toEqual({
      taskId: HELD_TASK,
      zoneName: "Zone 2",
      question: "Water Zone 2?",
      why: "I held this because rain is coming.",
      soil: { value: 20, fieldCapacity: 32 },
      rainMm: 12,
      percentFull: "About 63% full",
      waterMm: 20,
      open: true,
      stopped: false,
      work: null,
    });
  });

  it("closes once answered", () => {
    expect(decisionView(demo.day1Rejected, HELD_TASK)?.open).toBe(false);
  });

  it("is null for an unknown task", () => {
    expect(decisionView(demo.day1Held, 99)).toBeNull();
  });
});

describe("updatesView", () => {
  it("starts empty", () => {
    const view = updatesView(demo.seed);
    expect(view.items).toEqual([]);
    expect(view.undo).toBeNull();
  });

  it("records the farmer's no in their words", () => {
    const [first] = updatesView(demo.day1Rejected).items;
    expect(first?.title).toBe("You said no: wait for the rain");
    expect(first?.time).toBe("Today 6:00 am · Zone 2 · 20 mm");
  });

  it("day 2: newest first, in the design's order", () => {
    const view = updatesView(demo.day2Cycle);
    expect(view.items.map((item) => item.id)).toEqual([
      "water-2",
      "satellite-2",
      "report-2",
      "no-1",
      "report-1",
    ]);
    expect(view.items[0]?.title).toBe("Watering Zone 2 · 20 mm");
    expect(view.items[0]?.time).toBe("Today 6:00–9:20 am · Automatic");
    expect(view.items[4]?.title).toBe("Yesterday’s report");
    expect(view.unreadCount).toBe(1);
    // The ids leaving Updates marks read: exactly the unread ones.
    expect(view.unreadIds).toHaveLength(1);
    expect(view.unreadIds).toEqual(
      demo.day2Cycle.notifications.filter((notice) => notice.read_at === null).map((notice) => notice.id),
    );
  });

  it("day 2: offers the undo with the backend's window", () => {
    expect(updatesView(demo.day2Cycle).undo).toEqual({
      taskId: EXTRA_TASK,
      title: "Extra water, tomorrow",
      detail: "Zone 2 · 20 mm · 6:00 am",
      timeLeft: "6 h 00 min",
      remaining: 1,
    });
  });

  it("after the undo: the card turns into the confirmation", () => {
    const view = updatesView(demo.day2Undone);
    expect(view.undo).toBeNull();
    expect(view.undone).toBe("Cancelled. No water used.");
    expect(view.items.some((item) => item.id === `cancelled-${EXTRA_TASK}`)).toBe(true);
  });

  it("never offers an undo once the window has closed", () => {
    const tasks = demo.day2Cycle.tasks.map((task) =>
      task.id === EXTRA_TASK
        ? { ...task, status: "executed" as const, revert_open: false, revert_remaining_seconds: 0 }
        : task,
    );
    const executions = demo.day2Cycle.executions.map((event) => ({
      ...event,
      task_id: EXTRA_TASK,
    }));
    const [row] = updatesView({ ...demo.day2Cycle, tasks, executions }).items;
    expect(row?.time).toBe("Today 6:00–9:20 am · Automatic");
  });

  it("names an older report by its date alone", () => {
    const later = { ...demo.day2Cycle.clock, now: "2026-11-05T11:00:00Z" };
    const titles = updatesView({ ...demo.day2Cycle, clock: later }).items.map((item) => item.title);
    expect(titles).toContain("Report · Monday, 2 Nov");
  });

  describe("alerts the farmer must not miss", () => {
    const failedExtra = demo.day2Cycle.tasks.map((task) =>
      task.id === EXTRA_TASK ? { ...task, status: "failed" as const, revert_open: false } : task,
    );

    it("lists a watering that failed", () => {
      const view = updatesView({ ...demo.day2Cycle, tasks: failedExtra });
      const row = view.items.find((item) => item.id === `failed-${EXTRA_TASK}`);
      expect(row?.title).toBe("Watering didn’t run · Zone 2 · 20 mm");
      expect(row?.kind).toBe("problem");
      expect(row?.unread).toBe(true);
    });

    it("leaves a re-check failure to its card", () => {
      const failure = { ...demo.day2Cycle.verdicts[0]!, task_id: EXTRA_TASK, inputs: { recheck_verdict: {} } };
      const view = updatesView({ ...demo.day2Cycle, tasks: failedExtra, failures: [failure] });
      expect(view.items.some((item) => item.id === `failed-${EXTRA_TASK}`)).toBe(false);
      expect(view.rare.map((item) => item.kind)).toEqual(["recheck"]);
    });

    it("lists an alert with no task, in the backend's words", () => {
      const notice = {
        id: 9,
        message: "El ciclo diario se detuvo sin terminar",
        created_at: "2026-11-03T11:00:00Z",
        task_id: null,
        read_at: null,
        revert_deadline: null,
      };
      const view = updatesView({ ...demo.day2Cycle, notifications: [notice] });
      expect(view.items.find((item) => item.id === "alert-9")).toEqual({
        id: "alert-9",
        kind: "alert",
        title: notice.message,
        lang: "es",
        group: "Today",
        time: "Today 6:00 am",
        timeInDay: "6:00 am",
        href: null,
        unread: true,
      });
      expect(view.unreadCount).toBe(1);
    });

    it("keeps a planned watering in view once its undo window closes", () => {
      const tasks = demo.day2Cycle.tasks.map((task) =>
        task.id === EXTRA_TASK ? { ...task, revert_open: false } : task,
      );
      const row = updatesView({ ...demo.day2Cycle, tasks }).items.find(
        (item) => item.id === `planned-${EXTRA_TASK}`,
      );
      expect(row?.title).toBe("Watering planned · Zone 2 · 20 mm");
      expect(row?.time).toBe("Tomorrow 6:00 am");
      // Filed under the day it was planned, so its time keeps the day it runs.
      expect(row?.group).toBe("Today");
      expect(row?.timeInDay).toBe("Tomorrow 6:00 am");
    });

    it("files rows under their day and drops the day the heading says", () => {
      const items = updatesView(demo.day2Cycle).items;
      expect(items.map((item) => item.group)).toEqual(
        items.map((item) => (item.id.endsWith("-1") ? "Yesterday" : "Today")),
      );
      const watered = items.find((item) => item.id === "water-2");
      expect(watered?.time).toBe("Today 6:00–9:20 am · Automatic");
      expect(watered?.timeInDay).toBe("6:00–9:20 am · Automatic");
    });

    it("adds no such row while the undo card is showing", () => {
      const ids = updatesView(demo.day2Cycle).items.map((item) => item.id);
      expect(ids).not.toContain(`planned-${EXTRA_TASK}`);
    });
  });

  describe("an undo says what it really did", () => {
    const stopped = {
      ...demo.day2Undone,
      reverts: demo.day2Undone.reverts.map((revert) => ({
        ...revert,
        inputs: { ...revert.inputs, applied_mm: 8 },
      })),
    };

    it("admits water that had already gone on", () => {
      const view = updatesView(stopped);
      expect(view.undone).toBe("Stopped. 8 mm had already gone on.");
      const row = view.items.find((item) => item.id === `cancelled-${EXTRA_TASK}`);
      expect(row?.title).toBe("You stopped watering · Zone 2 · 8 of 20 mm");
    });

    it("says so on the plan too", () => {
      const [extra] = planView(stopped).days[2]?.tasks ?? [];
      expect(extra?.why).toBe("You stopped this while it ran. 8 mm had already gone on.");
    });

    it("keeps the plain wording when no water went on", () => {
      const [extra] = planView(demo.day2Undone).days[2]?.tasks ?? [];
      expect(extra?.why).toBe("You cancelled this before it ran.");
    });
  });

  it("lets an old rare case go, and shows a new one", () => {
    const event = demo.day2Cycle.verdicts[0]!;
    const refusal = (occurredAt: string) => ({ ...event, task_id: EXTRA_TASK, occurred_at: occurredAt });
    const old = updatesView({ ...demo.day2Cycle, refusals: [refusal("2026-11-01T11:00:00Z")] });
    expect(old.rare).toEqual([]);
    const recent = updatesView({ ...demo.day2Cycle, refusals: [refusal("2026-11-03T10:00:00Z")] });
    expect(recent.rare.map((item) => item.kind)).toEqual(["too_late"]);
  });

  it("shows no rare case on the demo", () => {
    expect(updatesView(demo.day2Undone).rare).toEqual([]);
  });

  it("classifies the rare cases from the event log", () => {
    const base: LogEvent = {
      id: 1,
      kind: "x",
      actor: "system",
      reason: "r",
      occurred_at: "2026-11-03T11:00:00Z",
      task_id: EXTRA_TASK,
      autonomy_level: null,
      rule: null,
      inputs: {},
    };
    const view = updatesView({
      ...demo.day2Cycle,
      failures: [
        {
          ...base,
          inputs: { recheck_verdict: { violations: [{ params: { forecast_mm: 8 } }] } },
        },
      ],
      notices: [{ ...base, inputs: { simulator_state_resumed: false } }],
      refusals: [base],
    });
    expect(view.rare.map((item) => item.kind)).toEqual(["recheck", "cut_off", "too_late"]);
    expect(view.rare[0]?.detail).toBe("Rain is now coming · 8 mm");
    expect(view.rare[2]?.detail).toBe("Zone 2 · 20 mm already in the soil");
  });
});

describe("fieldView", () => {
  it("states what the satellite found, marked as a simulated image", () => {
    const view = fieldView(demo.day1Held);
    expect(view?.headline).toBe("Plants in Zone 2 look weak");
    expect(view?.detail).toBe("I found 3 bare spots.");
    expect(view?.barePct).toBe("25%");
    expect(view?.caption).toBe("Simulated satellite image · 28 Oct");
    expect(view?.spots).toHaveLength(3);
  });

  it("prepares the question Ask about this puts in the Talk box", () => {
    expect(fieldView(demo.day1Held)?.question).toBe(
      "Why do the plants in Zone 2 look weak, and what can I do?",
    );
  });

  it("is null without a scene", () => {
    const imagery = { scene: null, zones: [], boxes: [] };
    expect(fieldView({ ...demo.seed, imagery })).toBeNull();
  });
});

describe("zoneView", () => {
  it("day 1: one reading, valve closed", () => {
    const view = zoneView(demo.day1Held, ZONE_ID);
    expect(view?.status).toBe("Dry");
    expect(view?.display).toBe("20%");
    expect(view?.needsMore).toBe("Zone 2 needs about 12% more to be full.");
    expect(view?.history).toEqual([20]);
    expect(view?.valve).toBe("Closed");
    expect(view?.sensor).toBe("OK · 6:00 am");
    expect(view?.caption).toBe("0.5 ha · maize");
  });

  it("opened from day 1's report on day 2: the soil of that morning, no valve or sensor", () => {
    const report = demo.day2Cycle.reports.find((candidate) => candidate.id === 1);
    const view = zoneView(demo.day2Cycle, ZONE_ID, report?.created_at);
    expect(view?.display).toBe("20%");
    expect(view?.asOf).toEqual({ label: "As it was on Monday, 2 Nov · 6:00 am", nowHref: "#/zone/1" });
    expect(zoneView(demo.day2Cycle, ZONE_ID)?.asOf).toBeNull();
  });

  it("says so when the moment is older than every reading", () => {
    const view = zoneView(demo.day2Cycle, ZONE_ID, "2026-10-01T11:00:00Z");
    expect(view?.display).toBe("—");
    expect(view?.needsMore).toBe("No soil reading from that time.");
  });

  it("day 2: the valve is open while the 20 mm runs", () => {
    const view = zoneView(demo.day2Cycle, ZONE_ID);
    expect(view?.status).toBe("Very dry");
    expect(view?.history).toEqual([20, 16.7]);
    expect(view?.valve).toBe("Open until 9:20 am");
    expect(view?.level).toBe("bad");
    expect(view?.percentFull).toBe("About 52% full");
    expect(view?.trend).toBe("Down from 20% about a day ago");
    expect(view?.valveLevel).toBe("info");
    expect(view?.sensorLevel).toBe("good");
  });

  it("reads the valve closed once a restart cut the watering off", () => {
    const notice = {
      ...demo.day2Cycle.executions[0]!,
      kind: "notification",
      inputs: { simulator_state_resumed: false },
    };
    const view = zoneView({ ...demo.day2Cycle, notices: [notice] }, ZONE_ID);
    expect(view?.valve).toBe("Closed");
  });

  it("is null for another zone", () => {
    expect(zoneView(demo.day1Held, 99)).toBeNull();
  });
});

describe("reportView", () => {
  it("day 1, read on day 2: the rows as of that morning, and the no after it", () => {
    const view = reportView(demo.day2Cycle, 1);
    expect(view?.title).toBe("Yesterday’s report");
    expect(view?.dateLine).toBe("Monday, 2 Nov · 6:00 am");
    expect(view?.tiles.map((tile) => [tile.value, tile.note, tile.label])).toEqual([
      ["20%", "of 32% full", "Zone 2 is dry"],
      ["12 mm", null, "Rain today"],
    ]);
    expect(view?.seen.map((item) => item.detail)).toEqual(["About 25% of the field shows bare soil."]);
    expect(view?.done).toEqual([]);
    // Said no since: the decision is closed, so the card explains and offers no button.
    expect(view?.next).toEqual([
      {
        kind: "waiting",
        title: "FieldPilot wants to water 20 mm",
        detail: "That is 20 litres per square metre. It waits for your OK.",
        href: null,
        action: null,
      },
    ]);
    expect(view?.fullLanguage).toBe("Spanish");
    expect(view?.saidNo?.detail).toBe("6:00 am · “Wait for the rain”");
    expect(view?.other?.label).toBe("Today · Tue 3 Nov");
  });

  it("day 2: the watering and the undoable extra", () => {
    const view = reportView(demo.day2Cycle, 2);
    expect(view?.title).toBe("Today’s report");
    expect(view?.tiles.map((tile) => [tile.value, tile.label, tile.href])).toEqual([
      ["16.7%", "Zone 2 is very dry", "#/zone/1?at=2026-11-03T11%3A00%3A00Z"],
      ["0 mm", "No rain today", null],
    ]);
    expect(view?.done.map((item) => [item.title, item.detail])).toEqual([
      ["FieldPilot is watering 20 mm", "20 litres on every square metre of Zone 2. Running until 9:20 am."],
    ]);
    expect(view?.next.map((item) => [item.title, item.detail, item.href, item.action])).toEqual([
      [
        "Watering tomorrow: 20 mm",
        "FieldPilot opens the valve on its own and gives Zone 2 20 litres per square metre.",
        "#/plan",
        "See it or undo",
      ],
    ]);
    expect(view?.saidNo).toBeNull();
    expect(view?.other?.label).toBe("Yesterday · Mon 2 Nov");
    expect(view?.full).toContain("16,7 %");
  });

  it("says the watering finished once its end has passed", () => {
    const later = { ...demo.day2Cycle, clock: { ...demo.day2Cycle.clock, now: "2026-11-03T20:00:00Z" } };
    expect(reportView(later, 2)?.done[0]?.detail).toBe(
      "20 litres on every square metre of Zone 2. Finished at 9:20 am.",
    );
  });

  it("is null for an unknown report", () => {
    expect(reportView(demo.day2Cycle, 99)).toBeNull();
  });
});

describe("planView", () => {
  it("gives the harvest form the crop, its dates and the waiting decision", () => {
    const harvest = planView(demo.day2Cycle).harvest;
    expect(harvest).toMatchObject({
      cycleId: 1,
      crop: "maize",
      sowingDate: "2026-10-01",
      today: "2026-11-03",
      areaHa: 2,
    });
    // A decision waiting or a watering still scheduled both hold the harvest back (D083 §6).
    const open = demo.day2Cycle.tasks.find(
      (task) => task.status === "pending_approval" || task.status === "scheduled",
    );
    expect(open).toBeDefined();
    expect(harvest?.openTask).toEqual({ id: open?.id, decision: open?.status === "pending_approval" });
  });

  it("has no harvest without a crop growing", () => {
    expect(planView({ ...demo.day2Cycle, cycle: null }).harvest).toBeNull();
  });

  it("hides the stage the seed cannot support", () => {
    const view = planView(demo.day2Cycle);
    expect(view.crop).toBe("Maize");
    expect(view.dayCount).toBe("Day 33");
    expect(view.stage).toBeNull();
  });

  it("lays out the days around today", () => {
    const { days } = planView(demo.day2Cycle);
    expect(days.map((day) => day.label)).toEqual(["Mon 2", "Today · Tue 3", "Wed 4", "Thu 5"]);
    expect(days[0]?.rain).toBe("Rain 12 mm expected");
    expect(days[3]?.tasks).toEqual([]);
  });

  it("gives each task its state", () => {
    const { days } = planView(demo.day2Cycle);
    const [no] = days[0]?.tasks ?? [];
    const [water, report] = days[1]?.tasks ?? [];
    const [extra] = days[2]?.tasks ?? [];
    expect(no?.state).toBe("said_no");
    expect(no?.when).toBe("Mon 2 Nov · held for rain");
    expect(water?.title).toBe("Watered Zone 2 · 20 mm");
    expect(water?.when).toBe("Today 6:00–9:20 am");
    expect(water?.source).toBe("Water helper");
    expect(water?.why).toBe("The soil was at 16.7%. All safety rules were OK.");
    expect(report?.source).toBe("Report writer");
    expect(extra?.state).toBe("can_undo");
    expect(extra?.undoTaskId).toBe(EXTRA_TASK);
  });

  it("links a waiting task to its decision", () => {
    const [held] = planView(demo.day1Held).days[0]?.tasks ?? [];
    expect(held?.state).toBe("needs_you");
    expect(held?.decideHref).toBe("#/decide/1");
  });

  it("marks an undone task cancelled", () => {
    const [extra] = planView(demo.day2Undone).days[2]?.tasks ?? [];
    expect(extra?.state).toBe("cancelled");
    expect(extra?.undoTaskId).toBeNull();
  });
});

describe("stopView", () => {
  it("names the running water it cannot stop", () => {
    expect(stopView(demo.day2Cycle).runningUntil).toBe("9:20 am");
    expect(stopView(demo.day1Held).runningUntil).toBeNull();
  });

  it("says what runs first once the farmer starts again", () => {
    expect(stopView(demo.day2Cycle).nextWatering).toBe("Next watering: Tomorrow 6:00 am");
    expect(stopView(demo.day1Held).nextWatering).toBe(
      "Next watering: Today 6:00 am, after your OK",
    );
    expect(stopView(demo.day2Undone).nextWatering).toBeNull();
  });

  it("says who stopped it", () => {
    const stop = { active: true, changed_at: "2026-11-02T12:12:00Z", changed_by: "farmer:dashboard" };
    expect(stopView({ ...demo.day1Held, stop }).since).toBe("Since 7:12 am · by you");
  });
});

describe("talkView", () => {
  const exchange = {
    id: 1,
    durationMs: 4_000,
    question: "¿Necesita agua el maíz de la zona dos?",
    answer: "Sí, la Zona 2 está seca.",
    lookedAt: ["soil", "rain"] as LookedAt[],
  };

  it("explains the mock-mode mic and links the waiting decision", () => {
    const view = talkView(demo.day1Held, []);
    expect(view.unavailable).toContain("live model");
    expect(view.decision?.taskId).toBe(HELD_TASK);
    expect(view.waitingCount).toBe(1);
  });

  it("says up front when the crop is one FieldPilot does not look after", () => {
    expect(talkView(demo.day1Held, []).manualCrop).toBeNull();
    const soy = { ...demo.day1Held, automated: false, cycle: demo.day1Held.cycle && { ...demo.day1Held.cycle, crop: "soybean" } };
    expect(talkView(soy, []).manualCrop).toBe("soybeans");
    expect(talkView({ ...soy, cycle: null }, []).manualCrop).toBeNull();
  });

  it("points a declined question to What to plant", () => {
    const declined = { ...exchange, offTopic: true };
    expect(talkView(demo.day1Held, [declined]).exchanges[0]?.elsewhere).toEqual({
      label: "See what to plant",
      href: "#/advice",
    });
    expect(talkView(demo.day1Held, [exchange]).exchanges[0]?.elsewhere).toBeNull();
  });

  it("lets the farmer ask on the live model", () => {
    expect(talkView({ ...demo.day1Held, chatLive: true }, []).unavailable).toBeNull();
  });

  it("keeps the agent's words and names what it read", () => {
    const [view] = talkView(demo.day1Held, [exchange]).exchanges;
    expect(view).toEqual({
      id: 1,
      duration: "0:04",
      question: exchange.question,
      answer: exchange.answer,
      chips: [
        { kind: "soil", text: "Soil 20% · full at 32%" },
        { kind: "rain", text: "Rain 12 mm · 24 h" },
      ],
      elsewhere: null,
    });
  });

  it("marks a typed question by having no recording", () => {
    const typed = { ...exchange, durationMs: null };
    expect(talkView(demo.day1Held, [typed]).exchanges[0]?.duration).toBeNull();
  });

  it("drops a source with no figure today", () => {
    const [view] = talkView(demo.day2Morning, [exchange]).exchanges;
    expect(view?.chips.map((chip) => chip.kind)).toEqual(["soil"]);
  });
});

function cycleOf(snapshot: FarmSnapshot): NonNullable<FarmSnapshot["cycle"]> {
  if (snapshot.cycle === null) throw new Error("The capture must hold a cycle");
  return snapshot.cycle;
}

describe("the harvest nudge on Today", () => {
  const cycle = cycleOf(demo.day1Held);

  it("stays quiet while the crop is far from ready", () => {
    expect(todayView(demo.day1Held).harvest).toBeNull();
  });

  it("says ready in the last stage, with what the form needs", () => {
    const stages = [
      ...cycle.stages.map((stage) => ({ ...stage, ended_at: stage.ended_at ?? "2026-11-01T11:00:00Z" })),
      { name: "maturity_harvest", started_at: "2026-11-01T11:00:00Z", ended_at: null, gdd_at_start: 1472.2 },
    ];
    const view = todayView({ ...demo.day1Held, cycle: { ...cycle, stages } });
    expect(view.harvest?.kind).toBe("ready");
    expect(view.harvest?.title).toBe("Your Maize looks ready to harvest");
    expect(view.harvest?.info.cycleId).toBe(cycle.id);
  });

  it("counts the days left when it is close", () => {
    const view = todayView({ ...demo.day1Held, cycle: { ...cycle, accumulated_gdd: 1400 } });
    expect(view.harvest?.kind).toBe("soon");
    expect(view.harvest?.title).toBe("Your Maize is nearly ready");
    expect(view.harvest?.detail).toMatch(/^About \d+ days? to go\. Get your bags ready\.$/);
  });

  it("only offers the form for a crop FieldPilot does not water", () => {
    const view = todayView({ ...demo.day1Held, automated: false, maturityGdd: null, stageOrder: [] });
    expect(view.harvest?.kind).toBe("record");
    expect(view.harvest?.title).toBe("Harvested your Maize?");
  });
});

describe("the planner's word on Plan", () => {
  it("says the pick and the chance it was sown with", () => {
    const planAtSowing = { model: "b1", rank: 2, p_success: 0.8 };
    expect(planView({ ...demo.day1Held, planAtSowing }).promise).toBe(
      "You planted pick #2 of that week. It does well about 8 years in 10.",
    );
  });

  it("says when the farmer chose outside the top 3", () => {
    const planAtSowing = { model: "b1", rank: 5, p_success: 0.42 };
    expect(planView({ ...demo.day1Held, ownRisk: true, planAtSowing }).promise).toBe(
      "You chose this crop yourself, outside my top 3. It does well about 4 years in 10.",
    );
    expect(planView({ ...demo.day1Held, ownRisk: true }).promise).toBe(
      "You chose this crop yourself, outside my top 3.",
    );
  });

  it("says nothing when the planner did not judge it", () => {
    expect(planView(demo.day1Held).promise).toBeNull();
  });
});
