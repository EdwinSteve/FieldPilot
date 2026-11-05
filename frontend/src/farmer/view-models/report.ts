import { plotDay } from "../../lib/format";
import type { Report, Task } from "../../types/api";
import { en } from "../i18n/en";
import { rejectionReason } from "../lib/eventInputs";
import {
  daysFromToday,
  formatCalendarDate,
  formatClock,
  formatDateLine,
  formatLongDate,
  relativeDay,
  shortWeekday,
} from "../lib/farmTime";
import { forecastOfDay } from "../lib/forecast";
import { irrigationRun } from "../lib/irrigationRun";
import { hrefOf } from "../lib/route";
import { bareSoilPct } from "./field";
import {
  eventOfTask,
  fieldCapacity,
  isWatering,
  plotOffset,
  soilAt,
  soilStatusLabel,
  volumeOf,
  zoneName,
  type FarmSnapshot,
} from "./snapshot";
import { soilStatus } from "../lib/soilStatus";
import { soilLevel } from "../lib/statusLevel";
import type { ReportItem, ReportTile, ReportView } from "./types";

function tasksOfDay(snapshot: FarmSnapshot, report: Report): Task[] {
  const offset = plotOffset(snapshot);
  const day = plotDay(report.created_at, offset);
  return snapshot.tasks.filter(
    (task) => isWatering(task) && plotDay(task.created_at, offset) === day,
  );
}

/** "tomorrow", "today", or "on Thu": the day of a planned watering, inside a sentence. */
function dayInSentence(iso: string, fromIso: string, offset: number): string {
  const days = daysFromToday(iso, fromIso, offset);
  const day = relativeDay(iso, fromIso, offset);
  return days >= -1 && days <= 1 ? day.toLowerCase() : en.report.onDay(day);
}

/** A task as the report found it: by its level, since its status may have changed since. */
function taskItem(snapshot: FarmSnapshot, report: Report, task: Task): ReportItem {
  const offset = plotOffset(snapshot);
  const mm = volumeOf(task);
  const zone = zoneName(snapshot);
  if (task.effective_level === "approval") {
    // The button only while the decision is still open; after it, "you said no" tells the rest.
    const open = task.status === "pending_approval";
    return {
      kind: "waiting",
      title: en.report.waitingTitle(mm),
      detail: en.report.waitingDetail(mm),
      href: open ? hrefOf({ screen: "decide", taskId: task.id }) : null,
      action: open ? en.report.decide : null,
    };
  }
  if (task.effective_level === "notify") {
    const undoable = task.status === "scheduled";
    return {
      kind: "planned",
      title: en.report.plannedTitle(mm, dayInSentence(task.scheduled_for, report.created_at, offset)),
      detail: en.report.plannedDetail(mm, zone),
      href: hrefOf({ screen: "plan" }),
      action: undoable ? en.report.seeOrUndo : en.report.seePlan,
    };
  }
  const execution = eventOfTask(snapshot.executions, task.id);
  const run = execution === null ? null : irrigationRun(execution);
  const running = run !== null && Date.parse(run.endsAt) > Date.parse(snapshot.clock.now);
  const when =
    run === null
      ? null
      : running
        ? en.report.runningUntil(formatClock(run.endsAt, offset))
        : en.report.finishedAt(formatClock(run.endsAt, offset));
  const litres = mm === null ? null : en.report.litres(mm, zone);
  return {
    kind: "done",
    title: running ? en.report.wateringTitle(mm) : en.report.wateredTitle(mm),
    detail: [litres, when].filter((part) => part !== null).join(" "),
    href: null,
    action: null,
  };
}

function tiles(snapshot: FarmSnapshot, report: Report): ReportTile[] {
  const offset = plotOffset(snapshot);
  const list: ReportTile[] = [];
  const soil = soilAt(snapshot, report.created_at);
  if (soil !== null) {
    list.push({
      kind: "soil",
      value: en.report.soilValue(soil.value),
      note: en.report.soilNote(soil.fieldCapacity),
      label: en.report.soilLabel(zoneName(snapshot), soilStatusLabel(soil)),
      level: soilLevel(soilStatus(soil.value, soil.fieldCapacity)),
      // The zone as it was when the report was written, not as it is now.
      href:
        snapshot.zone?.id === undefined
          ? null
          : hrefOf({ screen: "zone", zoneId: snapshot.zone.id, at: report.created_at }),
    });
  }
  const rainMm = forecastOfDay(snapshot.verdicts, report.created_at, offset);
  if (rainMm !== null) {
    list.push({
      kind: "rain",
      value: en.report.rainValue(rainMm),
      note: null,
      label: rainMm > 0 ? en.report.rainToday : en.report.noRainToday,
      level: "info",
      href: null,
    });
  }
  return list;
}

function seen(snapshot: FarmSnapshot): ReportItem[] {
  if (snapshot.imagery.zones[0]?.low_vigor !== true) return [];
  return [
    {
      kind: "satellite",
      title: en.report.satelliteTitle,
      detail: en.report.satelliteDetail(bareSoilPct(snapshot)),
      href: hrefOf({ screen: "field" }),
      action: null,
    },
  ];
}

function saidNo(snapshot: FarmSnapshot, report: Report): ReportView["saidNo"] {
  const offset = plotOffset(snapshot);
  const rejected = tasksOfDay(snapshot, report).find((task) => task.status === "rejected");
  if (rejected === undefined) return null;
  const rejection = eventOfTask(snapshot.rejections, rejected.id);
  if (rejection === null) return null;
  return {
    detail: en.report.saidNoDetail(
      formatClock(rejection.occurred_at, offset),
      rejectionReason(rejection),
    ),
  };
}

function otherReport(snapshot: FarmSnapshot, report: Report): ReportView["other"] {
  const offset = plotOffset(snapshot);
  const index = snapshot.reports.findIndex((candidate) => candidate.id === report.id);
  const other = snapshot.reports[index - 1] ?? snapshot.reports[index + 1];
  if (other === undefined) return null;
  const date = plotDay(other.created_at, offset);
  return {
    label: en.report.linkToDay(
      relativeDay(other.created_at, snapshot.clock.now, offset),
      `${shortWeekday(other.created_at, offset)} ${formatCalendarDate(date)}`,
    ),
    href: hrefOf({ screen: "report", reportId: other.id }),
  };
}

export function reportView(snapshot: FarmSnapshot, reportId: number): ReportView | null {
  const offset = plotOffset(snapshot);
  const report = snapshot.reports.find((candidate) => candidate.id === reportId);
  if (report === undefined) return null;
  const daysAgo = -daysFromToday(report.created_at, snapshot.clock.now, offset);
  const items = tasksOfDay(snapshot, report).map((task) => taskItem(snapshot, report, task));
  return {
    title: en.updates.reportTitle(daysAgo, formatLongDate(report.created_at, offset)),
    dateLine: formatDateLine(report.created_at, offset),
    soil: soilAt(snapshot, report.created_at) ?? {
      value: 0,
      fieldCapacity: fieldCapacity(snapshot),
    },
    tiles: tiles(snapshot, report),
    seen: seen(snapshot),
    done: items.filter((item) => item.kind === "done"),
    next: items.filter((item) => item.kind !== "done"),
    full: report.content,
    fullLanguage:
      report.language === "en" ? null : (en.report.languages[report.language] ?? report.language),
    saidNo: saidNo(snapshot, report),
    other: otherReport(snapshot, report),
  };
}
