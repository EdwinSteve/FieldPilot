import { useEffect, useMemo, useState } from "react";
import { api } from "../../api/endpoints";
import { useAction } from "../../hooks/useAction";
import { en } from "../i18n/en";
import { approvalOutcome, type ApprovalOutcome } from "../lib/approvalOutcome";
import { fromCache, toCache } from "../lib/farmCache";
import { stopView, talkView } from "../view-models/control";
import { decisionView } from "../view-models/decide";
import { fieldView } from "../view-models/field";
import { planView } from "../view-models/plan";
import { reportView } from "../view-models/report";
import type { FarmSnapshot } from "../view-models/snapshot";
import { todayView } from "../view-models/today";
import type { ChatExchange, Farm, FarmState } from "../view-models/types";
import { updatesView } from "../view-models/updates";
import { zoneView } from "../view-models/zone";
import { useFarmRefresh } from "./useFarmRefresh";
import { useFarmSnapshot } from "./useFarmSnapshot";
import { useTalk } from "./useTalk";

type FarmViews = Pick<
  Farm,
  "today" | "chat" | "updates" | "field" | "plan" | "stop" | "decision" | "zone" | "report"
>;

const CACHE_KEY = "fieldpilot.farm";
/** Long enough to read, short enough not to haunt the next screen. */
const FAILURE_NOTICE_MS = 6_000;

function readCachedFarm(): FarmSnapshot | null {
  try {
    return fromCache(window.localStorage.getItem(CACHE_KEY));
  } catch {
    return null;
  }
}

function cacheFarm(snapshot: FarmSnapshot): void {
  try {
    window.localStorage.setItem(CACHE_KEY, toCache(snapshot));
  } catch {
    // Private mode or a full disk: the app simply has no fallback.
  }
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
export function useFarm(): FarmState {
  const { version, refresh } = useFarmRefresh();
  const { data: fresh, error, loading } = useFarmSnapshot(version);
  const [cached] = useState(readCachedFarm);
  const data = fresh ?? (error === null ? null : cached);
  const action = useAction(refresh);
  const talk = useTalk(data?.plot.id);
  const [actionFailed, setActionFailed] = useState(false);

  useEffect(() => {
    if (fresh !== null) cacheFarm(fresh);
  }, [fresh]);

  useEffect(() => {
    if (!actionFailed) return undefined;
    const timer = window.setTimeout(() => setActionFailed(false), FAILURE_NOTICE_MS);
    return () => window.clearTimeout(timer);
  }, [actionFailed]);

  const { exchanges } = talk;
  const views = useMemo(() => (data ? viewsOf(data, exchanges) : null), [data, exchanges]);

  if (loading) return { status: "loading" };
  if (data === null && error !== null) return { status: "error" };
  if (data === null || views === null) return { status: "empty" };

  // `useAction` keeps the failure to itself, so success is noted inside the act.
  const attempt = async (act: () => Promise<unknown>): Promise<boolean> => {
    let done = false;
    await action.run(async () => {
      await act();
      done = true;
    });
    setActionFailed(!done);
    return done;
  };

  const unread = data.notifications.filter((notice) => notice.read_at === null);
  const farm: Farm = {
    ...views,
    approve: async (taskId) => {
      let outcome: ApprovalOutcome | null = null;
      await attempt(async () => {
        outcome = approvalOutcome((await api.approve(taskId)).status);
      });
      return outcome;
    },
    reject: (taskId, reason) => attempt(() => api.reject(taskId, reason)),
    undo: (taskId) => attempt(() => api.revert(taskId)),
    markAllRead: () =>
      attempt(() => Promise.all(unread.map((notice) => api.markRead(notice.id)))),
    setStopped: (stopped) => attempt(() => api.setEmergencyStop(stopped)),
    busy: action.busy,
    actionFailed,
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
  return { status: "ready", farm, stale: error !== null };
}
