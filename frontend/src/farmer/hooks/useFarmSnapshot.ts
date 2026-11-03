import { ApiError } from "../../api/client";
import { api } from "../../api/endpoints";
import { fetchHealth } from "../../api/health";
import { useCallback } from "react";
import { useResource, type Resource } from "../../hooks/useResource";
import type { Imagery, SensorReadings } from "../../types/api";
import type { FarmSnapshot } from "../view-models/snapshot";

const SOIL_MOISTURE = "soil_moisture";
const READINGS = 200;
const EVENTS = 200;

function soilReadings(sensors: SensorReadings[]) {
  const sensor = sensors.find((candidate) => candidate.kind === SOIL_MOISTURE);
  return (sensor?.readings ?? []).toSorted(
    (a, b) => Date.parse(a.recorded_at) - Date.parse(b.recorded_at),
  );
}

/**
 * Only crops stage 2 runs have a catalogue entry (maize today, D083); any other
 * crop is a manual record, and its 404 means "no stages", not a farm that failed.
 */
function noStages(error: unknown): null {
  if (error instanceof ApiError && error.status === 404) return null;
  throw error;
}

/** No photo yet, as for a fresh plot. */
const NO_IMAGERY: Imagery = { scene: null, zones: [], boxes: [] };

/**
 * Imagery is read only for a plot with an automated crop (409 for a manual one,
 * D083): no photo there, not a farm that failed. The screens show "no photo".
 */
function noImagery(error: unknown): Imagery {
  if (error instanceof ApiError && (error.status === 404 || error.status === 409)) return NO_IMAGERY;
  throw error;
}

function events(kind: string) {
  return api.events({ kind, limit: EVENTS });
}

/** One consistent read of the farmer's plot, or null when it is gone. */
async function loadFarm(plotId: number): Promise<FarmSnapshot | null> {
  const plot = (await api.plots()).find((candidate) => candidate.id === plotId);
  if (plot === undefined) return null;
  const [
    health,
    clock,
    zones,
    cycles,
    tasks,
    notifications,
    reports,
    stop,
    imagery,
    verdicts,
    executions,
    failures,
    rejections,
    refusals,
    notices,
    reverts,
  ] = await Promise.all([
    fetchHealth(),
    api.clock(),
    api.zones(plot.id),
    api.cycles(),
    api.tasks(),
    api.notifications(),
    api.reports(),
    api.emergencyStop(),
    api.imagery(plot.id).catch(noImagery),
    events("gate_verdict"),
    events("execution"),
    events("execution_failed"),
    events("rejection"),
    events("revert_refused"),
    events("notification"),
    events("revert"),
  ]);
  const zone = zones[0] ?? null;
  // Tasks, cycles, reports and the log are still one list for the whole deployment
  // (D082): keep this plot's, so a farmer never sees another farm's work.
  const ours = new Set(cycles.filter((c) => c.plot_id === plot.id).map((c) => c.id));
  const cycle =
    cycles.find((c) => c.plot_id === plot.id && c.status === "active") ??
    cycles.find((c) => c.plot_id === plot.id) ??
    null;
  const ourTasks = tasks.filter((task) => ours.has(task.cycle_id));
  const taskIds = new Set(ourTasks.map((task) => task.id));
  const onOurs = <T extends { task_id: number | null }>(items: T[]) =>
    items.filter((item) => item.task_id === null || taskIds.has(item.task_id));
  const [sensors, crop] = await Promise.all([
    zone === null ? [] : api.readings(zone.id, READINGS),
    cycle === null ? null : api.crop(cycle.crop).catch(noStages),
  ]);
  return {
    chatLive: !health.mock_llm,
    plot,
    clock,
    zone,
    readings: soilReadings(sensors),
    cycle,
    stageOrder: crop?.stages.map((stage) => stage.name) ?? [],
    tasks: ourTasks,
    notifications: onOurs(notifications),
    reports: reports.filter((report) => ours.has(report.cycle_id)),
    stop,
    imagery,
    verdicts: onOurs(verdicts),
    executions: onOurs(executions),
    failures: onOurs(failures),
    rejections: onOurs(rejections),
    reverts: onOurs(reverts),
    refusals: onOurs(refusals),
    notices: onOurs(notices),
  };
}

export function useFarmSnapshot(version: number, plotId: number): Resource<FarmSnapshot | null> {
  return useResource(
    useCallback(() => loadFarm(plotId), [plotId]),
    version,
  );
}
