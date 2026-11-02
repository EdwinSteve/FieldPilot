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
import { activeRun } from "../lib/irrigationRun";
import { cropLabel, farmLabel } from "../lib/names";
import { hrefOf } from "../lib/route";
import { rainLevel } from "../lib/rainLevel";
import { soilTrend } from "../lib/soilTrend";
import { plantsLevel, worstLevel } from "../lib/statusLevel";
import {
  fieldCapacity,
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
import type { DecisionLink, TodayView, UpdateItem, WeekDay } from "./types";
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

function statusDetail(rainMm: number | null): string {
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
    const water = snapshot.tasks.some(
      (task) =>
        isWatering(task) &&
        (task.status === "pending_approval" ||
          task.status === "scheduled" ||
          task.status === "executed") &&
        plotDay(task.scheduled_for, offset) === day,
    );
    return { day: shortWeekday(dayIso, offset), today, water, rain: today && (rainMm ?? 0) > 0 };
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
    time: en.today.undoLeft(undo.timeLeft),
    href: hrefOf({ screen: "updates" }),
    unread: false,
  };
  return [undoRow, ...items.slice(0, RECENT_UPDATES - 1)];
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
    dateLine: formatDateLine(snapshot.clock.now, offset),
    greeting: greeting(snapshot),
    farmLine: farmLine(snapshot),
    decision: firstDecision(snapshot),
    stoppedBanner: stoppedBanner(snapshot),
    zoneId: snapshot.zone?.id ?? 0,
    status,
    statusLabel: en.levels[status],
    statusTitle: statusLabel === null ? en.soil.noReading : en.soil.zoneIs(zone, statusLabel),
    statusDetail: statusDetail(rainMm),
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
  };
}
