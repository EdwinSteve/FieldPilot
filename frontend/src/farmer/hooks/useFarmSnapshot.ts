import { ApiError } from "../../api/client";
import { api } from "../../api/endpoints";
import { fetchHealth } from "../../api/health";
import { useCallback } from "react";
import { useResource, type Resource } from "../../hooks/useResource";
import { lifecycle } from "../api/lifecycle";
import type { Imagery, SensorReadings } from "../../types/api";
import { neediestZone } from "../lib/zones";
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
    weather,
  ] = await Promise.all([
    fetchHealth(),
    api.clock(),
    api.zones(plot.id),
    // The farmer's own route: it also says how each cycle runs and what the planner said.
    lifecycle.cycles(),
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
    // The forecast the gate reads (D095); an older backend without it falls back to the verdicts.
    api.weather(plot.id).catch(() => null),
  ]);
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
  // Every zone's soil: a plot can have several, and the screens lead with the neediest.
  const [perZone, crop] = await Promise.all([
    Promise.all(zones.map(async (z) => ({ zone: z, readings: soilReadings(await api.readings(z.id, READINGS)) }))),
    cycle === null ? null : api.crop(cycle.crop).catch(noStages),
  ]);
  const lead = neediestZone(perZone);
  return {
    chatLive: !health.mock_llm,
    health,
    weather,
    plot,
    clock,
    zone: lead?.zone ?? null,
    readings: lead?.readings ?? [],
    zones: perZone,
    cycle,
    stageOrder: crop?.stages.map((stage) => stage.name) ?? [],
    maturityGdd: crop?.maturity_gdd ?? null,
    automated: cycle?.automated ?? false,
    ownRisk: cycle?.own_risk ?? false,
    planAtSowing: cycle?.plan ?? null,
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
