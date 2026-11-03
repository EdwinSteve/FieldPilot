import { formatDuration } from "../../lib/format";
import type { Task } from "../../types/api";
import { en } from "../i18n/en";
import {
  appliedMm,
  isInterruptedWatering,
  isRecheckFailure,
  recheckRainMm,
  rejectionReason,
} from "../lib/eventInputs";
import {
  dayHeading,
  daysFromToday,
  formatClock,
  formatClockRange,
  formatDateLine,
  formatLongDate,
  relativeDay,
} from "../lib/farmTime";
import { activeRun, irrigationRun } from "../lib/irrigationRun";
import { newestRecent } from "../lib/recentEvent";
import { hrefOf } from "../lib/route";
import { undoRemaining } from "../lib/undoProgress";
import {
  eventOfTask,
  isWatering,
  plotOffset,
  volumeOf,
  zoneName,
  type FarmSnapshot,
} from "./snapshot";
import type { RareCase, UndoItem, UpdateItem, UpdatesView } from "./types";

interface Dated {
  at: number;
  item: UpdateItem;
}

type Stamp = Pick<UpdateItem, "group" | "time" | "timeInDay">;

/**
 * Where a row sits and what time it shows. `atIso` files it under a day;
 * `timeIso` is the moment its words name, which a planned watering puts ahead.
 */
function stamp(snapshot: FarmSnapshot, atIso: string, timeIso: string, rest: string): Stamp {
  const offset = plotOffset(snapshot);
  const now = snapshot.clock.now;
  const time = en.updates.at(relativeDay(timeIso, now, offset), rest);
  const sameDay = daysFromToday(atIso, now, offset) === daysFromToday(timeIso, now, offset);
  return { group: dayHeading(atIso, now, offset), time, timeInDay: sameDay ? rest : time };
}

function isUnread(snapshot: FarmSnapshot, taskId: number): boolean {
  return snapshot.notifications.some(
    (notice) => notice.task_id === taskId && notice.read_at === null,
  );
}

function levelLabel(task: Task): string {
  if (task.revert_open === true) return en.autonomy.canUndo;
  return task.effective_level === "approval" ? en.updates.youApproved : en.autonomy.automatic;
}

function wateredRow(snapshot: FarmSnapshot, task: Task): Dated | null {
  const offset = plotOffset(snapshot);
  const now = snapshot.clock.now;
  const zone = zoneName(snapshot);
  const execution = eventOfTask(snapshot.executions, task.id);
  const run = execution === null ? null : irrigationRun(execution);
  if (run === null) return null;
  const running =
    activeRun(snapshot.executions, snapshot.tasks, snapshot.notices, now)?.taskId === task.id;
  const mm = volumeOf(task);
  return {
    at: Date.parse(run.startedAt),
    item: {
      id: `water-${task.id}`,
      kind: "water",
      title: running ? en.updates.watering(zone, mm) : en.updates.watered(zone, mm),
      ...stamp(
        snapshot,
        run.startedAt,
        run.startedAt,
        en.updates.wateringTime(formatClockRange(run.startedAt, run.endsAt, offset), levelLabel(task)),
      ),
      href: hrefOf({ screen: "plan" }),
      unread: isUnread(snapshot, task.id),
    },
  };
}

function saidNoRow(snapshot: FarmSnapshot, task: Task): Dated {
  const offset = plotOffset(snapshot);
  const rejection = eventOfTask(snapshot.rejections, task.id);
  const at = rejection?.occurred_at ?? task.updated_at;
  const reason = rejection === null ? null : rejectionReason(rejection);
  return {
    at: Date.parse(at),
    item: {
      id: `no-${task.id}`,
      kind: "said_no",
      title: reason === null ? en.updates.saidNo : en.updates.saidNoBecause(reason),
      ...stamp(
        snapshot,
        at,
        at,
        en.updates.saidNoTime(formatClock(at, offset), zoneName(snapshot), volumeOf(task)),
      ),
      href: hrefOf({ screen: "plan" }),
      unread: isUnread(snapshot, task.id),
    },
  };
}

function appliedBeforeUndo(snapshot: FarmSnapshot, task: Task): number {
  const revert = eventOfTask(snapshot.reverts, task.id);
  return revert === null ? 0 : appliedMm(revert);
}

function cancelledRow(snapshot: FarmSnapshot, task: Task): Dated {
  const offset = plotOffset(snapshot);
  const applied = appliedBeforeUndo(snapshot, task);
  return {
    at: Date.parse(task.updated_at),
    item: {
      id: `cancelled-${task.id}`,
      kind: "said_no",
      title:
        applied > 0
          ? en.updates.stoppedRow(zoneName(snapshot), applied, volumeOf(task))
          : en.updates.cancelledRow(zoneName(snapshot), volumeOf(task)),
      ...stamp(snapshot, task.updated_at, task.updated_at, formatClock(task.updated_at, offset)),
      href: hrefOf({ screen: "plan" }),
      unread: isUnread(snapshot, task.id),
    },
  };
}

/** A failed task, unless the re-check's own card already explains it (D033). */
function failedRow(snapshot: FarmSnapshot, task: Task): Dated | null {
  const offset = plotOffset(snapshot);
  const failure = eventOfTask(snapshot.failures, task.id);
  if (failure !== null && isRecheckFailure(failure)) return null;
  const at = failure?.occurred_at ?? task.updated_at;
  return {
    at: Date.parse(at),
    item: {
      id: `failed-${task.id}`,
      kind: "problem",
      title: isWatering(task)
        ? en.updates.didntRun(zoneName(snapshot), volumeOf(task))
        : en.updates.actionDidntRun,
      ...stamp(snapshot, at, at, formatClock(at, offset)),
      href: hrefOf({ screen: "plan" }),
      unread: isUnread(snapshot, task.id),
    },
  };
}

/** A planned watering past its undo window: until then the undo card speaks for it. */
function plannedRow(snapshot: FarmSnapshot, task: Task): Dated | null {
  if (task.revert_open === true) return null;
  const offset = plotOffset(snapshot);
  return {
    at: Date.parse(task.created_at),
    item: {
      id: `planned-${task.id}`,
      kind: "water",
      title: en.updates.planned(zoneName(snapshot), volumeOf(task)),
      ...stamp(
        snapshot,
        task.created_at,
        task.scheduled_for,
        formatClock(task.scheduled_for, offset),
      ),
      href: hrefOf({ screen: "plan" }),
      unread: isUnread(snapshot, task.id),
    },
  };
}

function taskRow(snapshot: FarmSnapshot, task: Task): Dated | null {
  if (task.status === "failed") return failedRow(snapshot, task);
  if (!isWatering(task)) return null;
  if (task.status === "executed") return wateredRow(snapshot, task);
  if (task.status === "rejected") return saidNoRow(snapshot, task);
  if (task.status === "reverted") return cancelledRow(snapshot, task);
  return task.status === "scheduled" ? plannedRow(snapshot, task) : null;
}

/** Alerts about the system, not a task. The API gives no type, so they keep its words. */
function alertRows(snapshot: FarmSnapshot): Dated[] {
  const offset = plotOffset(snapshot);
  return snapshot.notifications
    .filter((notice) => notice.task_id === null)
    .map((notice) => ({
      at: Date.parse(notice.created_at),
      item: {
        id: `alert-${notice.id}`,
        kind: "alert",
        title: notice.message,
        lang: "es",
        ...stamp(snapshot, notice.created_at, notice.created_at, formatClock(notice.created_at, offset)),
        href: null,
        unread: notice.read_at === null,
      },
    }));
}

function reportRows(snapshot: FarmSnapshot): Dated[] {
  const offset = plotOffset(snapshot);
  const now = snapshot.clock.now;
  const newestId = snapshot.reports.at(-1)?.id;
  const weak = snapshot.imagery.zones[0]?.low_vigor === true;
  return snapshot.reports.flatMap((report) => {
    const at = Date.parse(report.created_at);
    const time = formatClock(report.created_at, offset);
    const date = formatLongDate(report.created_at, offset);
    const rows: Dated[] = [];
    if (report.id === newestId && weak) {
      rows.push({
        at,
        item: {
          id: `satellite-${report.id}`,
          kind: "satellite",
          title: en.updates.plantsWeak(zoneName(snapshot)),
          ...stamp(snapshot, report.created_at, report.created_at, en.updates.satelliteTime(time)),
          href: hrefOf({ screen: "field" }),
          unread: false,
        },
      });
    }
    const daysAgo = -daysFromToday(report.created_at, now, offset);
    rows.push({
      at,
      item: {
        id: `report-${report.id}`,
        kind: "report",
        title: en.updates.reportTitle(daysAgo, date),
        ...stamp(snapshot, report.created_at, report.created_at, time),
        href: hrefOf({ screen: "report", reportId: report.id }),
        unread: false,
      },
    });
    return rows;
  });
}

function undoItem(snapshot: FarmSnapshot): UndoItem | null {
  const offset = plotOffset(snapshot);
  const task = snapshot.tasks.find((candidate) => candidate.revert_open === true);
  if (task === undefined || task.revert_deadline === null) return null;
  const remaining = task.revert_remaining_seconds ?? 0;
  return {
    taskId: task.id,
    title: en.updates.undoTitle(relativeDay(task.scheduled_for, snapshot.clock.now, offset)),
    detail: en.updates.undoDetail(
      zoneName(snapshot),
      volumeOf(task),
      formatClock(task.scheduled_for, offset),
    ),
    timeLeft: formatDuration(remaining),
    remaining: undoRemaining(task.created_at, task.revert_deadline, remaining),
  };
}

/** What an undo did, while its task's time is ahead or it happened today. */
function undoneNote(snapshot: FarmSnapshot): string | null {
  const now = snapshot.clock.now;
  const task = snapshot.tasks.find(
    (candidate) =>
      candidate.status === "reverted" &&
      (Date.parse(candidate.scheduled_for) > Date.parse(now) ||
        daysFromToday(candidate.updated_at, now, plotOffset(snapshot)) === 0),
  );
  if (task === undefined) return null;
  const applied = appliedBeforeUndo(snapshot, task);
  return applied > 0 ? en.updates.stoppedEarly(applied) : en.updates.cancelled;
}

function rareCases(snapshot: FarmSnapshot): RareCase[] {
  const zone = zoneName(snapshot);
  const now = snapshot.clock.now;
  const cases: RareCase[] = [];
  const recheck = newestRecent(snapshot.failures.filter(isRecheckFailure), now);
  if (recheck !== null) {
    cases.push({
      kind: "recheck",
      title: en.updates.rare.recheckTitle,
      detail: en.updates.rare.recheckDetail(recheckRainMm(recheck)),
      note: en.updates.rare.recheckNote,
    });
  }
  if (newestRecent(snapshot.notices.filter(isInterruptedWatering), now) !== null) {
    cases.push({
      kind: "cut_off",
      title: en.updates.rare.cutOffTitle,
      detail: en.updates.rare.cutOffDetail(zone),
      note: en.updates.rare.cutOffNote,
      zoneHref: hrefOf({ screen: "zone", zoneId: snapshot.zone?.id ?? 0 }),
      action: en.updates.rare.cutOffAction(zone),
    });
  }
  const refused = newestRecent(snapshot.refusals, now);
  if (refused !== null) {
    const task = snapshot.tasks.find((candidate) => candidate.id === refused.task_id);
    cases.push({
      kind: "too_late",
      title: en.updates.rare.tooLateTitle,
      detail: en.updates.rare.tooLateDetail(zone, task === undefined ? null : volumeOf(task)),
    });
  }
  return cases;
}

export function updatesView(snapshot: FarmSnapshot): UpdatesView {
  const dated = [
    ...snapshot.tasks.flatMap((task) => taskRow(snapshot, task) ?? []),
    ...alertRows(snapshot),
    ...reportRows(snapshot),
  ];
  return {
    dateLine: formatDateLine(snapshot.clock.now, plotOffset(snapshot)),
    undo: undoItem(snapshot),
    undone: undoneNote(snapshot),
    rare: rareCases(snapshot),
    items: dated.toSorted((a, b) => b.at - a.at).map(({ item }) => item),
    unreadCount: snapshot.notifications.filter((notice) => notice.read_at === null).length,
  };
}
