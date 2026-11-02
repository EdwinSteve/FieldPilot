import { api } from "../../api/endpoints";
import { fetchHealth } from "../../api/health";
import { useResource, type Resource } from "../../hooks/useResource";
import type { SensorReadings } from "../../types/api";
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

function events(kind: string) {
  return api.events({ kind, limit: EVENTS });
}

/** One consistent read of the farm, or null before any farm exists. */
async function loadFarm(): Promise<FarmSnapshot | null> {
  const [plot] = await api.plots();
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
    api.imagery(plot.id),
    events("gate_verdict"),
    events("execution"),
    events("execution_failed"),
    events("rejection"),
    events("revert_refused"),
    events("notification"),
    events("revert"),
  ]);
  const zone = zones[0] ?? null;
  const sensors = zone === null ? [] : await api.readings(zone.id, READINGS);
  return {
    chatLive: !health.mock_llm,
    plot,
    clock,
    zone,
    readings: soilReadings(sensors),
    cycle: cycles.find((cycle) => cycle.plot_id === plot.id) ?? null,
    tasks,
    notifications,
    reports,
    stop,
    imagery,
    verdicts,
    executions,
    failures,
    rejections,
    reverts,
    refusals,
    notices,
  };
}

export function useFarmSnapshot(version: number): Resource<FarmSnapshot | null> {
  return useResource(loadFarm, version);
}
