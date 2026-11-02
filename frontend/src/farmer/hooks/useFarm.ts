import { useMemo } from "react";
import { api } from "../../api/endpoints";
import { useAction } from "../../hooks/useAction";
import { en } from "../i18n/en";
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
  const { data, error, loading } = useFarmSnapshot(version);
  const action = useAction(refresh);
  const talk = useTalk(data?.plot.id);
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
    return done;
  };

  const unread = data.notifications.filter((notice) => notice.read_at === null);
  const farm: Farm = {
    ...views,
    approve: (taskId) => attempt(() => api.approve(taskId)),
    reject: (taskId, reason) => attempt(() => api.reject(taskId, reason)),
    undo: (taskId) => attempt(() => api.revert(taskId)),
    markAllRead: () =>
      attempt(() => Promise.all(unread.map((notice) => api.markRead(notice.id)))),
    setStopped: (stopped) => attempt(() => api.setEmergencyStop(stopped)),
    busy: action.busy,
    actionFailed: action.error !== null,
    talk: {
      status: talk.status,
      failure: talk.failure === null ? null : en.talk.failures[talk.failure],
      pendingQuestion: talk.pendingQuestion,
      draft: talk.draft,
      setDraft: talk.setDraft,
      sendDraft: talk.sendDraft,
      toggleMic: talk.toggleMic,
      cancel: talk.cancel,
    },
  };
  return { status: "ready", farm, stale: error !== null };
}
