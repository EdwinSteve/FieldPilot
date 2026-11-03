import { plotDay } from "../../lib/format";
import { daysSinceSowing } from "../../lib/stages";
import type { Report, Task } from "../../types/api";
import { en } from "../i18n/en";
import { appliedMm, gateFacts } from "../lib/eventInputs";
import {
  daysFromToday,
  formatCalendarDate,
  formatClock,
  formatClockRange,
  plusDays,
  relativeDay,
  shortWeekday,
} from "../lib/farmTime";
import { forecastOfDay } from "../lib/forecast";
import { irrigationRun } from "../lib/irrigationRun";
import { cropLabel } from "../lib/names";
import { hrefOf } from "../lib/route";
import { roundReading } from "../lib/soilStatus";
import { visibleStage } from "../lib/visibleStage";
import { eventOfTask, isWatering, plotOffset, volumeOf, zoneName, type FarmSnapshot } from "./snapshot";
import type { PlanDay, PlanStage, PlanTask, PlanView, TaskState } from "./types";

const DAYS_AHEAD = 2;

function dateLabel(iso: string, offset: number): string {
  return `${shortWeekday(iso, offset)} ${formatCalendarDate(plotDay(iso, offset))}`;
}

function shortDayLabel(iso: string, offset: number): string {
  return `${shortWeekday(iso, offset)} ${Number(plotDay(iso, offset).slice(8))}`;
}

function waterState(task: Task): TaskState {
  if (task.revert_open === true) return "can_undo";
  switch (task.status) {
    case "pending_approval":
      return "needs_you";
    case "scheduled":
      return "planned";
    case "executed":
      return "done";
    case "rejected":
      return "said_no";
    case "reverted":
      return "cancelled";
    case "failed":
      return "failed";
  }
}

const STATE_LABELS: Record<TaskState, string> = {
  done: en.plan.states.done,
  automatic: en.autonomy.automatic,
  can_undo: en.autonomy.canUndo,
  said_no: en.plan.states.said_no,
  needs_you: en.autonomy.needsYou,
  planned: en.plan.states.scheduled,
  cancelled: en.plan.states.cancelled,
  failed: en.plan.states.failed,
};

function whenOf(snapshot: FarmSnapshot, task: Task, state: TaskState, heldForRain: boolean): string {
  const offset = plotOffset(snapshot);
  const now = snapshot.clock.now;
  if (state === "said_no" && heldForRain) {
    return en.plan.heldForRain(dateLabel(task.scheduled_for, offset));
  }
  const execution = eventOfTask(snapshot.executions, task.id);
  const run = execution === null ? null : irrigationRun(execution);
  if (state === "done" && run !== null) {
    const range = formatClockRange(run.startedAt, run.endsAt, offset);
    return `${relativeDay(run.startedAt, now, offset)} ${range}`;
  }
  return `${dateLabel(task.scheduled_for, offset)} · ${formatClock(task.scheduled_for, offset)}`;
}

function whyOf(snapshot: FarmSnapshot, task: Task, state: TaskState): string {
  const verdict = eventOfTask(snapshot.verdicts, task.id);
  const facts = verdict === null ? null : gateFacts(verdict);
  switch (state) {
    case "said_no":
      return en.plan.whyNo(facts?.rainMm ?? null);
    case "cancelled": {
      const revert = eventOfTask(snapshot.reverts, task.id);
      const applied = revert === null ? 0 : appliedMm(revert);
      return applied > 0 ? en.plan.whyStopped(applied) : en.plan.whyCancelled;
    }
    case "failed":
      return en.plan.whyFailed;
    case "needs_you":
      return en.plan.whyWaiting;
    case "can_undo":
    case "planned":
      return en.plan.whyExtra(zoneName(snapshot));
    default:
      return en.plan.whyDone(
        facts === null || facts.soilPct === null ? null : roundReading(facts.soilPct),
      );
  }
}

function sourceOf(snapshot: FarmSnapshot, task: Task): string {
  const verdict = eventOfTask(snapshot.verdicts, task.id);
  const proposedBy = verdict === null ? null : gateFacts(verdict).proposedBy;
  return proposedBy === "agent:irrigation" ? en.plan.sources.water : en.plan.sources.other;
}

function titleOf(snapshot: FarmSnapshot, task: Task, state: TaskState): string {
  const zone = zoneName(snapshot);
  const mm = volumeOf(task);
  if (state === "done") return en.updates.watered(zone, mm);
  if (task.action_type === "extra_irrigation") return en.plan.extraTitle(zone, mm);
  return en.plan.waterTitle(zone, mm);
}

function waterTask(snapshot: FarmSnapshot, task: Task): PlanTask {
  const state = waterState(task);
  const heldForRain = eventOfTask(snapshot.verdicts, task.id)?.rule === "rain_forecast_above_limit";
  return {
    id: `task-${task.id}`,
    kind: "water",
    title: titleOf(snapshot, task, state),
    when: whenOf(snapshot, task, state, heldForRain),
    state,
    stateLabel: STATE_LABELS[state],
    source: sourceOf(snapshot, task),
    why: whyOf(snapshot, task, state),
    undoTaskId: state === "can_undo" ? task.id : null,
    decideHref: state === "needs_you" ? hrefOf({ screen: "decide", taskId: task.id }) : null,
  };
}

function reportTask(snapshot: FarmSnapshot, report: Report): PlanTask {
  const offset = plotOffset(snapshot);
  const day = relativeDay(report.created_at, snapshot.clock.now, offset);
  return {
    id: `report-${report.id}`,
    kind: "report",
    title: en.plan.reportTitle,
    when: `${day} ${formatClock(report.created_at, offset)}`,
    state: "automatic",
    stateLabel: STATE_LABELS.automatic,
    source: en.plan.sources.report,
    why: en.plan.whyReport,
    undoTaskId: null,
    decideHref: null,
  };
}

function dayOf(snapshot: FarmSnapshot, dayIso: string): PlanDay {
  const offset = plotOffset(snapshot);
  const day = plotDay(dayIso, offset);
  const today = daysFromToday(dayIso, snapshot.clock.now, offset) === 0;
  const rainMm = forecastOfDay(snapshot.verdicts, dayIso, offset);
  const label = shortDayLabel(dayIso, offset);
  return {
    label: today ? en.plan.dayToday(label) : label,
    today,
    rain: rainMm !== null && rainMm > 0 ? en.plan.rainExpected(rainMm) : null,
    tasks: [
      ...snapshot.tasks
        .filter((task) => isWatering(task) && plotDay(task.scheduled_for, offset) === day)
        .map((task) => waterTask(snapshot, task)),
      ...snapshot.reports
        .filter((report) => plotDay(report.created_at, offset) === day)
        .map((report) => reportTask(snapshot, report)),
    ],
  };
}

/** From the earliest task or report through a couple of days ahead. */
function days(snapshot: FarmSnapshot): PlanDay[] {
  const offset = plotOffset(snapshot);
  const now = snapshot.clock.now;
  const instants = [
    ...snapshot.tasks.filter(isWatering).map((task) => task.scheduled_for),
    ...snapshot.reports.map((report) => report.created_at),
  ];
  const offsets = instants.map((iso) => daysFromToday(iso, now, offset));
  const first = Math.min(0, ...offsets);
  const last = Math.max(DAYS_AHEAD, ...offsets);
  return Array.from({ length: last - first + 1 }, (_, index) =>
    dayOf(snapshot, plusDays(now, first + index)),
  );
}

function stageName(code: string): string {
  // A crop without English names yet still reads as words, not a code.
  return en.plan.stages[code] ?? code.replaceAll("_", " ");
}

function stage(snapshot: FarmSnapshot, dayCount: number): PlanStage | null {
  if (snapshot.cycle === null) return null;
  const visible = visibleStage(snapshot.stageOrder, snapshot.cycle.stages, dayCount);
  if (visible === null) return null;
  return {
    steps: visible.steps,
    now: en.plan.now(stageName(visible.current)),
    next: visible.next === null ? null : en.plan.next(stageName(visible.next)),
  };
}

export function planView(snapshot: FarmSnapshot): PlanView {
  const offset = plotOffset(snapshot);
  const cycle = snapshot.cycle;
  const dayCount = cycle === null ? 0 : daysSinceSowing(cycle.sowing_date, snapshot.clock.now, offset);
  return {
    crop: cycle === null ? "" : cropLabel(cycle.crop),
    dayCount: en.plan.dayCount(dayCount),
    stage: stage(snapshot, dayCount),
    days: days(snapshot),
  };
}
