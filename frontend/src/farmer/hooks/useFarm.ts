import { useEffect, useMemo, useState } from "react";
import { api } from "../../api/endpoints";
import { useAction } from "../../hooks/useAction";
import type { Resource } from "../../hooks/useResource";
import type { Task } from "../../types/api";
import { en } from "../i18n/en";
import { actionFailure, type ActionFailure } from "../lib/actionFailure";
import { approvalOutcome, type ApprovalOutcome } from "../lib/approvalOutcome";
import { fromCache, toCache, type CachedFarm } from "../lib/farmCache";
import { formatClock } from "../lib/farmTime";
import { ageText } from "../lib/freshness";
import { buzz } from "../lib/haptic";
import { stopView, talkView } from "../view-models/control";
import { decisionView } from "../view-models/decide";
import { fieldView } from "../view-models/field";
import { planView } from "../view-models/plan";
import { reportView } from "../view-models/report";
import type { FarmSnapshot } from "../view-models/snapshot";
import { todayView } from "../view-models/today";
import type { Approval, ChatExchange, Farm, FarmState } from "../view-models/types";
import { updatesView } from "../view-models/updates";
import { zoneView } from "../view-models/zone";
import { useFarmRefresh } from "./useFarmRefresh";
import { useFarmSnapshot } from "./useFarmSnapshot";
import { useOnline } from "./useOnline";
import { useOutbox } from "./useOutbox";
import { useTalk } from "./useTalk";

type FarmViews = Pick<
  Farm,
  "today" | "chat" | "updates" | "field" | "plan" | "stop" | "decision" | "zone" | "report"
>;

const CACHE_KEY = "fieldpilot.farm";
/** Long enough to read, short enough not to haunt the next screen. */
const FAILURE_NOTICE_MS = 6_000;

function readCachedFarm(): CachedFarm | null {
  try {
    return fromCache(window.localStorage.getItem(CACHE_KEY));
  } catch {
    return null;
  }
}

function cacheFarm(snapshot: FarmSnapshot, savedAt: number): void {
  try {
    window.localStorage.setItem(CACHE_KEY, toCache(snapshot, savedAt));
  } catch {
    // Private mode or a full disk: the app simply has no fallback.
  }
}

/** Real times of the reads, as asked for: the last good one, and the last that came back at all. */
interface Reads {
  resource: Resource<FarmSnapshot | null>;
  freshAt: number | null;
  settledAt: number;
  retrying: boolean;
}

function nextReads(reads: Reads, resource: Resource<FarmSnapshot | null>, now: number): Reads {
  if (resource.loading) return { ...reads, resource };
  const freshData = resource.data !== null && resource.data !== reads.resource.data;
  return {
    resource,
    freshAt: freshData ? now : reads.freshAt,
    settledAt: now,
    retrying: false,
  };
}

/** No signal, or the farm out of reach: the answer can wait on the phone. A refusal cannot. */
function canWait(failure: ActionFailure): boolean {
  return failure === "offline" || failure === "unreachable";
}

/** A real moment as the phone's own clock reads it, "10:42 am". */
export function phoneClock(ms: number): string {
  const offsetHours = -new Date(ms).getTimezoneOffset() / 60;
  return formatClock(new Date(ms).toISOString(), offsetHours);
}

function viewsOf(snapshot: FarmSnapshot, exchanges: ChatExchange[]): FarmViews {
  return {
    today: todayView(snapshot),
    chat: talkView(snapshot, exchanges),
    updates: updatesView(snapshot),
    field: fieldView(snapshot),
    plan: planView(snapshot),
    stop: stopView(snapshot),
    decision: (taskId) => decisionView(snapshot, taskId),
    zone: (zoneId) => zoneView(snapshot, zoneId),
    report: (reportId) => reportView(snapshot, reportId),
  };
}

/** The farm as the screens see it: fresh views, and actions that report success. */
export function useFarm(plotId: number): FarmState {
  const { version, requestedAt, refresh } = useFarmRefresh();
  const resource = useFarmSnapshot(version, plotId);
  const { data: fresh, error, loading } = resource;
  // A copy saved for another plot is not this farm.
  const [cached] = useState(() => {
    const saved = readCachedFarm();
    return saved?.snapshot.plot.id === plotId ? saved : null;
  });
  const data = fresh ?? (error === null ? null : (cached?.snapshot ?? null));
  const action = useAction(refresh);
  const talk = useTalk(data?.plot.id);
  const online = useOnline();
  const outbox = useOutbox(fresh, online, refresh);
  const [failure, setFailure] = useState<ActionFailure | null>(null);
  const [reads, setReads] = useState<Reads>(() => ({
    resource,
    freshAt: null,
    settledAt: requestedAt,
    retrying: false,
  }));
  let current = reads;
  // Each read, failed or not, hands back a new resource: that is the moment it settled.
  if (reads.resource !== resource) {
    current = nextReads(reads, resource, requestedAt);
    setReads(current);
  }
  const { freshAt, settledAt, retrying } = current;

  useEffect(() => {
    if (fresh !== null) cacheFarm(fresh, Date.now());
  }, [fresh]);

  useEffect(() => {
    if (failure === null) return undefined;
    const timer = window.setTimeout(() => setFailure(null), FAILURE_NOTICE_MS);
    return () => window.clearTimeout(timer);
  }, [failure]);

  const { exchanges } = talk;
  const views = useMemo(() => (data ? viewsOf(data, exchanges) : null), [data, exchanges]);

  if (loading) return { status: "loading" };
  if (data === null && error !== null) {
    return {
      status: "error",
      retry: () => {
        setReads((previous) => ({ ...previous, retrying: true }));
        refresh();
      },
      retrying,
      lastTried: phoneClock(settledAt),
    };
  }
  if (data === null || views === null) return { status: "empty" };

  // `useAction` keeps the error to itself, so the act notes why it failed.
  const attempt = async (act: () => Promise<unknown>, felt = true): Promise<ActionFailure | null> => {
    if (felt) buzz();
    const result: { failure: ActionFailure | null } = { failure: "unreachable" };
    await action.run(async () => {
      try {
        await act();
        result.failure = null;
      } catch (caught) {
        result.failure = actionFailure(caught, navigator.onLine);
        throw caught;
      }
    });
    setFailure(result.failure);
    return result.failure;
  };
  const tried = async (act: () => Promise<unknown>, felt = true) => (await attempt(act, felt)) === null;
  const offset = data.plot.utc_offset_hours;

  const lastGoodAt = freshAt ?? cached?.savedAt ?? null;

  const unread = data.notifications.filter((notice) => notice.read_at === null);
  const farm: Farm = {
    ...views,
    approve: async (taskId): Promise<Approval | null> => {
      const answered: { task: Task | null } = { task: null };
      const missed = await attempt(async () => {
        answered.task = await api.approve(taskId);
      });
      const task = answered.task;
      if (missed === null && task !== null) {
        const outcome: ApprovalOutcome = approvalOutcome(task.status);
        const undoUntil =
          task.revert_open === true && task.revert_deadline !== null
            ? formatClock(task.revert_deadline, offset)
            : null;
        return { outcome, undoUntil };
      }
      if (missed === null || !canWait(missed)) return null;
      outbox.save({ taskId, answer: "yes", savedAt: Date.now() });
      setFailure(null);
      return { outcome: "saved", undoUntil: null };
    },
    reject: async (taskId, reason) => {
      const missed = await attempt(() => api.reject(taskId, reason));
      if (missed === null) return "sent";
      if (!canWait(missed)) return null;
      outbox.save({ taskId, answer: "no", ...(reason === undefined ? {} : { reason }), savedAt: Date.now() });
      setFailure(null);
      return "saved";
    },
    savedAnswers: outbox.answers.map((answer) => answer.taskId),
    outboxNotice: outbox.notice,
    undo: (taskId) => tried(() => api.revert(taskId)),
    markAllRead: () =>
      tried(() => Promise.all(unread.map((notice) => api.markRead(notice.id))), false),
    setStopped: (stopped) => tried(() => api.setEmergencyStop(stopped)),
    busy: action.busy,
    actionFailure: failure,
    talk: {
      status: talk.status,
      failure: talk.failure === null ? null : en.talk.failures[talk.failure],
      pendingQuestion: talk.pendingQuestion,
      draft: talk.draft,
      setDraft: talk.setDraft,
      sendDraft: talk.sendDraft,
      ask: talk.ask,
      toggleMic: talk.toggleMic,
      cancel: talk.cancel,
    },
  };
  return {
    status: "ready",
    farm,
    stale: error !== null,
    age: lastGoodAt === null ? null : ageText(lastGoodAt, settledAt),
  };
}
