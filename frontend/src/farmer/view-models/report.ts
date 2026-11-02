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
import type { ReportRow, ReportView } from "./types";

function tasksOfDay(snapshot: FarmSnapshot, report: Report): Task[] {
  const offset = plotOffset(snapshot);
  const day = plotDay(report.created_at, offset);
  return snapshot.tasks.filter(
    (task) => isWatering(task) && plotDay(task.created_at, offset) === day,
  );
}

/** A task as the report found it: by its level, since its status may have changed since. */
function taskRow(snapshot: FarmSnapshot, report: Report, task: Task): ReportRow {
  const offset = plotOffset(snapshot);
  const mm = volumeOf(task);
  if (task.effective_level === "approval") return { kind: "waiting", text: en.report.waiting(mm) };
  if (task.effective_level === "notify") {
    const day = relativeDay(task.scheduled_for, report.created_at, offset);
    return { kind: "planned", text: en.report.planned(mm, day) };
  }
  const execution = eventOfTask(snapshot.executions, task.id);
  const run = execution === null ? null : irrigationRun(execution);
  const until = run === null ? null : formatClock(run.endsAt, offset);
  return { kind: "done", text: en.report.wateringNow(mm, until) };
}

function rows(snapshot: FarmSnapshot, report: Report): ReportRow[] {
  const offset = plotOffset(snapshot);
  const list: ReportRow[] = [];
  const soil = soilAt(snapshot, report.created_at);
  if (soil !== null) {
    const text = en.report.soil(
      zoneName(snapshot),
      soilStatusLabel(soil),
      soil.value,
      soil.fieldCapacity,
    );
    list.push({ kind: "soil", text });
  }
  const rainMm = forecastOfDay(snapshot.verdicts, report.created_at, offset);
  if (rainMm !== null) {
    list.push(
      rainMm > 0
        ? { kind: "rain", text: en.report.rain(rainMm) }
        : { kind: "no_rain", text: en.report.noRain },
    );
  }
  list.push(...tasksOfDay(snapshot, report).map((task) => taskRow(snapshot, report, task)));
  if (snapshot.imagery.zones[0]?.low_vigor === true) {
    list.push({ kind: "satellite", text: en.report.satellite(bareSoilPct(snapshot)) });
  }
  return list;
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
  return {
    title: en.updates.reportTitle(daysAgo, formatLongDate(report.created_at, offset)),
    dateLine: formatDateLine(report.created_at, offset),
    soil: soilAt(snapshot, report.created_at) ?? {
      value: 0,
      fieldCapacity: fieldCapacity(snapshot),
    },
    rows: rows(snapshot, report),
    original: report.content,
    saidNo: saidNo(snapshot, report),
    other: otherReport(snapshot, report),
  };
}
