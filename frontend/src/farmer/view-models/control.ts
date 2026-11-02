// The Stop and Talk screens: small enough to share a file.
import { en } from "../i18n/en";
import { formatClock } from "../lib/farmTime";
import { activeRun } from "../lib/irrigationRun";
import { pendingTasks, plotOffset, type FarmSnapshot } from "./snapshot";
import { firstDecision } from "./today";
import type { StopView, TalkView } from "./types";

const FARMER_PREFIX = "farmer:";

export function stopView(snapshot: FarmSnapshot): StopView {
  const offset = plotOffset(snapshot);
  const { changed_at: changedAt, changed_by: changedBy } = snapshot.stop;
  const running = activeRun(snapshot.executions, snapshot.tasks, snapshot.clock.now);
  return {
    stopped: snapshot.stop.active,
    since:
      changedAt === null
        ? ""
        : en.stop.since(
            formatClock(changedAt, offset),
            changedBy?.startsWith(FARMER_PREFIX) === true,
          ),
    runningUntil: running === null ? null : formatClock(running.endsAt, offset),
  };
}

export function talkView(snapshot: FarmSnapshot): TalkView {
  return {
    micNote: snapshot.chatLive ? en.talk.comingSoon : en.talk.needsLiveModel,
    decision: firstDecision(snapshot),
    waitingCount: pendingTasks(snapshot).length,
  };
}
