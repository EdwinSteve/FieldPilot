// When water runs. No endpoint serves the valve, so this reads it from the execution log.
import type { LogEvent, Task } from "../../types/api";
import { executionFacts, isInterruptedWatering } from "./eventInputs";

const HOUR_MS = 3_600_000;

export interface IrrigationRun {
  taskId: number;
  startedAt: string;
  endsAt: string;
}

/** The run of an execution, or null when it adds no water (closing a valve, for one). */
export function irrigationRun(execution: LogEvent): IrrigationRun | null {
  const { startedAt, targetMm, rateMmPerHour } = executionFacts(execution);
  if (execution.task_id === null || startedAt === null) return null;
  if (targetMm === null || rateMmPerHour === null) return null;
  if (!(targetMm > 0) || !(rateMmPerHour > 0)) return null;
  const end = Date.parse(startedAt) + (targetMm / rateMmPerHour) * HOUR_MS;
  return { taskId: execution.task_id, startedAt, endsAt: new Date(end).toISOString() };
}

/** True when a stop command or a restart ended the run before its natural end. */
function endedEarly(
  run: IrrigationRun,
  executions: readonly LogEvent[],
  notices: readonly LogEvent[],
): boolean {
  const started = Date.parse(run.startedAt);
  const stopped = executions.some(
    (execution) =>
      execution.inputs.action_type === "stop_irrigation" &&
      Date.parse(execution.occurred_at) >= started,
  );
  return (
    stopped || notices.some((notice) => notice.task_id === run.taskId && isInterruptedWatering(notice))
  );
}

/** The run still going at `nowIso`. A reverted, failed or stopped run has no water left. */
export function activeRun(
  executions: readonly LogEvent[],
  tasks: readonly Task[],
  notices: readonly LogEvent[],
  nowIso: string,
): IrrigationRun | null {
  const now = Date.parse(nowIso);
  for (const execution of executions) {
    const run = irrigationRun(execution);
    if (run === null) continue;
    const task = tasks.find((candidate) => candidate.id === run.taskId);
    if (task?.status !== "executed" || endedEarly(run, executions, notices)) continue;
    if (Date.parse(run.startedAt) <= now && now < Date.parse(run.endsAt)) return run;
  }
  return null;
}
