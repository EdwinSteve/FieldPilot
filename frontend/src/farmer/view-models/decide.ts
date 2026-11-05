import { en } from "../i18n/en";
import { gateFacts } from "../lib/eventInputs";
import { formatClock, relativeDay } from "../lib/farmTime";
import { roundReading } from "../lib/soilStatus";
import { percentFull } from "../lib/soilTrend";
import {
  doseOf,
  eventOfTask,
  fieldCapacity,
  fieldWorkTitle,
  isFieldWork,
  plotOffset,
  zoneNameOf,
  questionOf,
  soilAt,
  volumeOf,
  zoneName,
  type FarmSnapshot,
} from "./snapshot";
import type { DecisionView } from "./types";

/** The question as the gate held it: the numbers it saw, not today's. */
export function decisionView(snapshot: FarmSnapshot, taskId: number): DecisionView | null {
  const task = snapshot.tasks.find((candidate) => candidate.id === taskId);
  if (task === undefined) return null;
  const verdict = eventOfTask(snapshot.verdicts, taskId);
  const facts = verdict === null ? null : gateFacts(verdict);
  const work = isFieldWork(task);
  const zone = work ? zoneNameOf(snapshot, task.zone_id) : zoneName(snapshot);
  const offset = plotOffset(snapshot);
  const soilPct = facts?.soilPct ?? soilAt(snapshot)?.value ?? 0;
  const rule = verdict?.rule ?? "";
  const soilValue = roundReading(soilPct);
  const capacity = fieldCapacity(snapshot);
  return {
    taskId,
    zoneName: zone,
    question: questionOf(task, zone),
    why: work ? en.fieldWork.approvalNote : (en.decide.holdReasons[rule] ?? en.decide.holdGeneric),
    soil: { value: soilValue, fieldCapacity: capacity },
    percentFull: en.soil.percentFull(percentFull(soilValue, capacity)),
    rainMm: facts?.rainMm ?? 0,
    waterMm: volumeOf(task),
    open: task.status === "pending_approval",
    stopped: snapshot.stop.active,
    work: work
      ? {
          title: fieldWorkTitle(task, zone),
          dose: doseOf(task),
          when: `${relativeDay(task.scheduled_for, snapshot.clock.now, offset)} · ${formatClock(task.scheduled_for, offset)}`,
          rationale: task.rationale,
        }
      : null,
  };
}
