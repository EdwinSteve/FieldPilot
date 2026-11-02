// The Stop and Talk screens: small enough to share a file.
import { en } from "../i18n/en";
import { formatClock } from "../lib/farmTime";
import { forecastOfDay } from "../lib/forecast";
import { activeRun } from "../lib/irrigationRun";
import { clipLength, type LookedAt } from "../lib/lookedAt";
import { pendingTasks, plotOffset, soilAt, type FarmSnapshot } from "./snapshot";
import { firstDecision } from "./today";
import type { ChatExchange, StopView, TalkChip, TalkExchange, TalkView } from "./types";

const FARMER_PREFIX = "farmer:";

export function stopView(snapshot: FarmSnapshot): StopView {
  const offset = plotOffset(snapshot);
  const { changed_at: changedAt, changed_by: changedBy } = snapshot.stop;
  const running = activeRun(snapshot.executions, snapshot.tasks, snapshot.notices, snapshot.clock.now);
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

/** A source named with the figure the farm shows now; none when there is no figure. */
function chipOf(snapshot: FarmSnapshot, source: LookedAt): TalkChip | null {
  if (source === "soil") {
    const soil = soilAt(snapshot);
    if (soil === null) return null;
    return { kind: source, text: en.talk.chipSoil(soil.value, soil.fieldCapacity) };
  }
  const rainMm = forecastOfDay(snapshot.verdicts, snapshot.clock.now, plotOffset(snapshot));
  return rainMm === null ? null : { kind: source, text: en.talk.chipRain(rainMm) };
}

function exchangeView(snapshot: FarmSnapshot, exchange: ChatExchange): TalkExchange {
  return {
    id: exchange.id,
    duration: exchange.durationMs === null ? null : clipLength(exchange.durationMs),
    question: exchange.question,
    answer: exchange.answer,
    chips: exchange.lookedAt.flatMap((source) => chipOf(snapshot, source) ?? []),
  };
}

export function talkView(snapshot: FarmSnapshot, exchanges: readonly ChatExchange[]): TalkView {
  return {
    unavailable: snapshot.chatLive ? null : en.talk.needsLiveModel,
    exchanges: exchanges.map((exchange) => exchangeView(snapshot, exchange)),
    decision: firstDecision(snapshot),
    waitingCount: pendingTasks(snapshot).length,
  };
}
