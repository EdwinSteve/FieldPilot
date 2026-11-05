import { plotDay } from "../../lib/format";
import { daysSinceSowing } from "../../lib/stages";
import { en } from "../i18n/en";
import {
  daysFromToday,
  formatDateLine,
  localHour,
  plusDays,
  shortWeekday,
} from "../lib/farmTime";
import { forecastOfDay } from "../lib/forecast";
import { harvestTiming } from "../lib/harvestTime";
import { activeRun } from "../lib/irrigationRun";
import { cropLabel, farmLabel, zoneLabel } from "../lib/names";
import { hrefOf } from "../lib/route";
import { rainLevel } from "../lib/rainLevel";
import { soilTrend } from "../lib/soilTrend";
import { plantsLevel, worstLevel, type Level } from "../lib/statusLevel";
import type { TodayHarvest } from "./types";
import {
  fieldCapacity,
  harvestInfo,
  isWatering,
  pendingTasks,
  plotOffset,
  questionOf,
  soilAt,
  soilLevelOf,
  soilStatusLabel,
  soilTileLabel,
  zoneName,
  type FarmSnapshot,
} from "./snapshot";
import type { DecisionLink, OtherZone, TodayView, UpdateItem, WeekDay } from "./types";
import { updatesView } from "./updates";

const MONDAY_INDEX = 1;
const NOON = 12;
const EVENING = 18;
const RECENT_UPDATES = 2;

export function firstDecision(snapshot: FarmSnapshot): DecisionLink | null {
  const task = pendingTasks(snapshot)[0];
  if (task === undefined) return null;
  return { taskId: task.id, question: questionOf(task, zoneName(snapshot)) };
}

function greeting(snapshot: FarmSnapshot): string {
  const hour = localHour(snapshot.clock.now, plotOffset(snapshot));
  if (hour < NOON) return en.time.greetings.morning;
  return hour < EVENING ? en.time.greetings.afternoon : en.time.greetings.evening;
}

function farmLine(snapshot: FarmSnapshot): string {
  const farm = farmLabel(snapshot.plot.name);
  if (snapshot.cycle === null) return farm;
  const day = daysSinceSowing(snapshot.cycle.sowing_date, snapshot.clock.now, plotOffset(snapshot));
  return en.today.farmLine(farm, cropLabel(snapshot.cycle.crop), day);
}

/** A watering waiting for the farmer, still ahead, or run today. */
function wateringInHand(snapshot: FarmSnapshot): boolean {
  const offset = plotOffset(snapshot);
  const now = snapshot.clock.now;
  return snapshot.tasks.some((task) => {
    if (!isWatering(task)) return false;
    if (task.status === "pending_approval") return true;
    if (task.status === "scheduled") return Date.parse(task.scheduled_for) >= Date.parse(now);
    return task.status === "executed" && daysFromToday(task.scheduled_for, now, offset) === 0;
  });
}

function checkedToday(snapshot: FarmSnapshot): boolean {
  const offset = plotOffset(snapshot);
  return snapshot.reports.some(
    (report) => daysFromToday(report.created_at, snapshot.clock.now, offset) === 0,
  );
}

/**
 * Dry soil with no watering in hand says why: the soil reading is live, but only
 * the morning check plans water. Otherwise the line is about the rain.
 */
function statusDetail(snapshot: FarmSnapshot, soilLevel: Level, rainMm: number | null): string {
  const needsWater = soilLevel === "bad" || soilLevel === "watch";
  if (needsWater && !wateringInHand(snapshot)) {
    return checkedToday(snapshot) ? en.today.noWaterPlanned : en.today.checkNotRun;
  }
  if (rainMm === null) return en.rain.notChecked;
  return rainMm > 0 ? en.rain.expected : en.rain.none;
}

function stoppedBanner(snapshot: FarmSnapshot): string | null {
  if (!snapshot.stop.active) return null;
  const running = activeRun(snapshot.executions, snapshot.tasks, snapshot.notices, snapshot.clock.now);
  return running === null ? en.stop.stopped : en.stop.stoppedWhileRunning;
}

/** Monday to Sunday of this week. Rain is one 24 h figure, so only today can show it. */
function week(snapshot: FarmSnapshot, rainMm: number | null): WeekDay[] {
  const offset = plotOffset(snapshot);
  const now = snapshot.clock.now;
  const shifted = new Date(Date.parse(now) + offset * 3_600_000);
  const daysSinceMonday = (shifted.getUTCDay() + 7 - MONDAY_INDEX) % 7;
  return Array.from({ length: 7 }, (_, index) => {
    const dayIso = plusDays(now, index - daysSinceMonday);
    const day = plotDay(dayIso, offset);
    const today = daysFromToday(dayIso, now, offset) === 0;
    const thatDay = snapshot.tasks.filter(
      (task) => isWatering(task) && plotDay(task.scheduled_for, offset) === day,
    );
    const water = thatDay.some(
      (task) =>
        task.status === "pending_approval" ||
        task.status === "scheduled" ||
        task.status === "executed",
    );
    const saidNo = !water && thatDay.some((task) => task.status === "rejected");
    return {
      day: shortWeekday(dayIso, offset),
      today,
      water,
      rain: today && (rainMm ?? 0) > 0,
      saidNo,
    };
  });
}

/** The newest updates, with an open undo first: it is the one that can run out. */
function recentUpdates(snapshot: FarmSnapshot): UpdateItem[] {
  const { undo, items } = updatesView(snapshot);
  if (undo === null) return items.slice(0, RECENT_UPDATES);
  const undoRow: UpdateItem = {
    id: `undo-${undo.taskId}`,
    kind: "undo",
    title: undo.title,
    group: "",
    time: en.today.undoLeft(undo.timeLeft),
    timeInDay: en.today.undoLeft(undo.timeLeft),
    href: hrefOf({ screen: "updates" }),
    unread: false,
  };
  return [undoRow, ...items.slice(0, RECENT_UPDATES - 1)];
}

function statusTitle(snapshot: FarmSnapshot, zone: string, statusLabel: string | null): string {
  if (snapshot.zone === null) return en.today.noSensors;
  return statusLabel === null ? en.soil.noReading : en.soil.zoneIs(zone, statusLabel);
}

/**
 * Near harvest time, Today says so and opens the form. A manual crop has no stages
 * to judge by, so from its first day it only offers the form, quietly.
 */
function harvestPrompt(snapshot: FarmSnapshot): TodayHarvest | null {
  const info = harvestInfo(snapshot);
  const cycle = snapshot.cycle;
  if (info === null || cycle === null) return null;
  const crop = cropLabel(info.crop);
  const days = daysSinceSowing(cycle.sowing_date, snapshot.clock.now, plotOffset(snapshot));
  if (!snapshot.automated) {
    if (days < 1) return null;
    return { kind: "record", title: en.harvestPrompt.recordTitle(crop), detail: en.harvestPrompt.recordDetail, info };
  }
  const timing = harvestTiming({
    currentStage: cycle.stages.find((stage) => stage.ended_at === null)?.name ?? null,
    stageOrder: snapshot.stageOrder,
    accumulatedGdd: cycle.accumulated_gdd,
    maturityGdd: snapshot.maturityGdd,
    daysSinceSowing: days,
  });
  if (timing.kind === "ready") {
    return { kind: "ready", title: en.harvestPrompt.readyTitle(crop), detail: en.harvestPrompt.readyDetail, info };
  }
  if (timing.kind === "soon") {
    return {
      kind: "soon",
      title: en.harvestPrompt.soonTitle(crop),
      detail: en.harvestPrompt.soonDetail(timing.days),
      info,
    };
  }
  return null;
}

/** The zones the card does not lead with, each with its soil now and a way in. */
function otherZones(snapshot: FarmSnapshot): OtherZone[] {
  return snapshot.zones
    .filter((entry) => entry.zone.id !== snapshot.zone?.id)
    .map((entry) => {
      const soil = soilAt({ ...snapshot, zone: entry.zone, readings: entry.readings });
      return {
        name: zoneLabel(entry.zone.name),
        status: soil === null ? en.soil.unknown : soilStatusLabel(soil),
        level: soil === null ? "neutral" : soilLevelOf(soil),
        display: soil === null ? en.soil.unknown : `${soil.value}%`,
        href: hrefOf({ screen: "zone", zoneId: entry.zone.id }),
      };
    });
}

export function todayView(snapshot: FarmSnapshot): TodayView {
  const offset = plotOffset(snapshot);
  const zone = zoneName(snapshot);
  const soil = soilAt(snapshot);
  const rainMm = forecastOfDay(snapshot.verdicts, snapshot.clock.now, offset);
  const imaging = snapshot.imagery.zones[0];
  const statusLabel = soil === null ? null : soilStatusLabel(soil);
  const soilTileLevel = soil === null ? "neutral" : soilLevelOf(soil);
  const plants = plantsLevel(imaging === undefined ? null : imaging.low_vigor);
  const status = worstLevel([soilTileLevel, plants]);
  return {
    otherZones: otherZones(snapshot),
    dateLine: formatDateLine(snapshot.clock.now, offset),
    greeting: greeting(snapshot),
    farmLine: farmLine(snapshot),
    decision: firstDecision(snapshot),
    stoppedBanner: stoppedBanner(snapshot),
    zoneId: snapshot.zone?.id ?? 0,
    status,
    statusLabel: en.levels[status],
    statusTitle: statusTitle(snapshot, zone, statusLabel),
    // A farm set up in the app has no zone or sensor yet (D083): say so, not "no reading".
    statusDetail:
      snapshot.zone === null
        ? en.today.noSensorsDetail
        : statusDetail(snapshot, soilTileLevel, rainMm),
    soil: {
      value: soil?.value ?? 0,
      fieldCapacity: fieldCapacity(snapshot),
      display: soil === null ? en.soil.unknown : String(soil.value),
      ofFull: soil === null ? null : en.soil.ofFull(soil.fieldCapacity),
      label: soil === null ? en.soil.tileUnknown : soilTileLabel(soil),
      level: soilTileLevel,
      trend: soilTrend(snapshot.readings, snapshot.clock.now)?.direction ?? null,
    },
    rain: {
      mm: rainMm ?? 0,
      known: rainMm !== null,
      display: rainMm === null ? en.rain.unknown : en.rain.amount(rainMm),
      label:
        rainMm === null ? en.rain.tileUnknown : en.rain.tile(en.rain.levels[rainLevel(rainMm)]),
    },
    plants: {
      value:
        imaging === undefined ? en.plants.unknown : imaging.low_vigor ? en.plants.weak : en.plants.ok,
      label: en.plants.label,
      level: plants,
    },
    recent: recentUpdates(snapshot),
    week: week(snapshot, rainMm),
    harvest: harvestPrompt(snapshot),
  };
}
