// The real API's answers along the demo script, captured from a replay (MOCK_LLM=1).
import type {
  Clock,
  Cycle,
  EmergencyStop,
  Imagery,
  LogEvent,
  Notification,
  Plot,
  Report,
  SensorReadings,
  Task,
  Zone,
} from "../../types/api";
import type { FarmSnapshot } from "../view-models/snapshot";
import day1Held from "./api/day1Held.json";
import day1Rejected from "./api/day1Rejected.json";
import day2Cycle from "./api/day2Cycle.json";
import day2Morning from "./api/day2Morning.json";
import day2Undone from "./api/day2Undone.json";
import seed from "./api/seed.json";

interface Capture {
  health: { mock_llm: boolean };
  plots: Plot[];
  clock: Clock;
  zones: Zone[];
  readings: SensorReadings[];
  cycles: Cycle[];
  tasks: Task[];
  notifications: Notification[];
  reports: Report[];
  stop: EmergencyStop;
  imagery: Imagery;
  events_gate_verdict: LogEvent[];
  events_execution: LogEvent[];
  events_execution_failed: LogEvent[];
  events_rejection: LogEvent[];
  events_revert: LogEvent[];
  events_revert_refused: LogEvent[];
}

const MAIZE_STAGES = [
  "sowing",
  "germination_emergence",
  "vegetative",
  "flowering",
  "grain_fill",
  "maturity_harvest",
];

function toSnapshot(raw: unknown): FarmSnapshot {
  const capture = raw as Capture;
  const [plot] = capture.plots;
  if (plot === undefined) throw new Error("A capture must hold the demo plot");
  return {
    chatLive: !capture.health.mock_llm,
    plot,
    clock: capture.clock,
    zone: capture.zones[0] ?? null,
    readings: capture.readings[0]?.readings ?? [],
    cycle: capture.cycles[0] ?? null,
    // The captures predate GET /crops (D077); maize is the crop they hold.
    stageOrder: MAIZE_STAGES,
    // Maize is run by stage 2; it is ready at 1472.2 GDD (config/crops/maize.yaml).
    maturityGdd: 1472.2,
    automated: true,
    ownRisk: false,
    planAtSowing: null,
    tasks: capture.tasks,
    notifications: capture.notifications,
    reports: capture.reports,
    stop: capture.stop,
    imagery: capture.imagery,
    verdicts: capture.events_gate_verdict,
    executions: capture.events_execution,
    failures: capture.events_execution_failed,
    rejections: capture.events_rejection,
    reverts: capture.events_revert,
    refusals: capture.events_revert_refused,
    notices: [],
  };
}

export const demo = {
  seed: toSnapshot(seed),
  day1Held: toSnapshot(day1Held),
  day1Rejected: toSnapshot(day1Rejected),
  day2Morning: toSnapshot(day2Morning),
  day2Cycle: toSnapshot(day2Cycle),
  day2Undone: toSnapshot(day2Undone),
};
