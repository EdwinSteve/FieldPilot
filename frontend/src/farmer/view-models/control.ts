// The Stop and Talk screens: small enough to share a file.
import { en } from "../i18n/en";
import { formatClock, relativeDay } from "../lib/farmTime";
import { forecastOfDay } from "../lib/forecast";
import { activeRun } from "../lib/irrigationRun";
import { clipLength, type LookedAt } from "../lib/lookedAt";
import { cropLabel } from "../lib/names";
import { hrefOf } from "../lib/route";
import { isWatering, pendingTasks, plotOffset, soilAt, type FarmSnapshot } from "./snapshot";
import { firstDecision } from "./today";
import type { ChatExchange, StopView, TalkChip, TalkExchange, TalkView } from "./types";

const FARMER_PREFIX = "farmer:";

/** The first watering still ahead, planned or waiting for the farmer. */
function nextWatering(snapshot: FarmSnapshot): string | null {
  const offset = plotOffset(snapshot);
  const now = snapshot.clock.now;
  const next = snapshot.tasks
    .filter(
      (task) =>
        isWatering(task) &&
        (task.status === "scheduled" || task.status === "pending_approval") &&
        Date.parse(task.scheduled_for) >= Date.parse(now),
    )
    .toSorted((a, b) => Date.parse(a.scheduled_for) - Date.parse(b.scheduled_for))
    .at(0);
  if (next === undefined) return null;
  return en.stop.nextWatering(
    relativeDay(next.scheduled_for, now, offset),
    formatClock(next.scheduled_for, offset),
    next.status === "pending_approval",
  );
}

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
    nextWatering: nextWatering(snapshot),
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
    // The chat keeps to the crop growing; what to sow next is on What to plant.
    elsewhere:
      exchange.offTopic === true ? { label: en.advice.seeWhatToPlant, href: hrefOf({ screen: "advice" }) } : null,
  };
}

/** "soybeans" when the crop growing runs by hand: the chat answers only about a crop FieldPilot runs. */
export function manualCrop(snapshot: FarmSnapshot): string | null {
  if (snapshot.cycle === null || snapshot.automated) return null;
  return cropLabel(snapshot.cycle.crop).toLowerCase();
}

export function talkView(snapshot: FarmSnapshot, exchanges: readonly ChatExchange[]): TalkView {
  return {
    unavailable: snapshot.chatLive ? null : en.talk.needsLiveModel,
    manualCrop: manualCrop(snapshot),
    exchanges: exchanges.map((exchange) => exchangeView(snapshot, exchange)),
    decision: firstDecision(snapshot),
    waitingCount: pendingTasks(snapshot).length,
  };
}
