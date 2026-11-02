import { en } from "../i18n/en";
import { gateFacts } from "../lib/eventInputs";
import { roundReading } from "../lib/soilStatus";
import {
  eventOfTask,
  fieldCapacity,
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
  const zone = zoneName(snapshot);
  const soilPct = facts?.soilPct ?? soilAt(snapshot)?.value ?? 0;
  const rule = verdict?.rule ?? "";
  return {
    taskId,
    zoneName: zone,
    question: questionOf(task, zone),
    why: en.decide.holdReasons[rule] ?? en.decide.holdGeneric,
    soil: { value: roundReading(soilPct), fieldCapacity: fieldCapacity(snapshot) },
    rainMm: facts?.rainMm ?? 0,
    waterMm: volumeOf(task),
    open: task.status === "pending_approval",
    stopped: snapshot.stop.active,
  };
}
