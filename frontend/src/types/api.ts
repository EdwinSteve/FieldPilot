// Response and request bodies of the backend (backend/app/api/schemas.py).
// Times are ISO 8601 strings in UTC; the UI formats them, never parses meaning.

export type TaskStatus =
  | "pending_approval"
  | "scheduled"
  | "executed"
  | "reverted"
  | "rejected"
  | "failed";

export type AutonomyLevel = "autonomous" | "notify" | "approval";

export type Json = string | number | boolean | null | Json[] | { [key: string]: Json };

export interface Plot {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  area_ha: number;
  utc_offset_hours: number;
}

export interface Zone {
  id: number;
  plot_id: number;
  name: string;
  area_ha: number;
  field_capacity_pct: number;
}

export interface Reading {
  value: number;
  recorded_at: string;
}

export interface SensorReadings {
  sensor_id: number;
  kind: string;
  unit: string;
  readings: Reading[];
}

export interface Stage {
  name: string;
  started_at: string;
  ended_at: string | null;
  gdd_at_start: number;
}

export interface Cycle {
  id: number;
  plot_id: number;
  crop: string;
  sowing_date: string;
  status: string;
  accumulated_gdd: number;
  gdd_updated_through: string | null;
  stages: Stage[];
}

export interface Task {
  id: number;
  cycle_id: number;
  zone_id: number | null;
  action_type: string;
  params: Record<string, Json>;
  scheduled_for: string;
  status: TaskStatus;
  effective_level: AutonomyLevel;
  rationale: string;
  created_at: string;
  updated_at: string;
  /** D011: the backend decides; the UI only displays. */
  revert_deadline: string | null;
  revert_open: boolean | null;
  revert_remaining_seconds: number | null;
  /** D067: why it is held, in the farmer's words. */
  reason_es: string | null;
}

export interface RevertResult {
  task: Task;
  requested_mm: number;
  applied_mm: number;
  applied_liters: number;
}

export interface LogEvent {
  id: number;
  kind: string;
  actor: string;
  reason: string;
  occurred_at: string;
  task_id: number | null;
  autonomy_level: AutonomyLevel | null;
  rule: string | null;
  inputs: Record<string, Json>;
}

export interface Notification {
  id: number;
  message: string;
  created_at: string;
  task_id: number | null;
  read_at: string | null;
  revert_deadline: string | null;
}

export interface Report {
  id: number;
  cycle_id: number;
  language: string;
  content: string;
  created_at: string;
}

export interface ChatAnswer {
  run_id: string;
  status: string;
  answer: string | null;
  turns: number;
}

export interface VoiceAnswer extends ChatAnswer {
  transcript: string;
}

export interface DailyCycleRun {
  run_id: string;
  subagent: string;
  status: string;
  turns: number;
}

export interface DailyCycleResult {
  session_id: string;
  status: string;
  stopped_at: string | null;
  runs: DailyCycleRun[];
  brief: Record<string, Json>;
}

export interface Clock {
  now: string;
  speed_factor: number;
  paused: boolean;
}

export type ClockChange =
  | { action: "pause" }
  | { action: "resume" }
  | { action: "speed"; speed_factor: number }
  | { action: "advance"; advance_seconds: number };

export interface TickResult {
  at: string;
  readings_recorded: number;
  tasks: Task[];
  days_counted: string[];
  zones_without_data: number[];
}

export interface EmergencyStop {
  active: boolean;
  changed_at: string | null;
  changed_by: string | null;
}

export interface ZoneImagery {
  zone_id: number;
  ndvi_mean: number | null;
  low_ndvi_pct: number | null;
  /** Approximate: from boxes, and null when unknown (D059). */
  bare_soil_pct: number | null;
  low_vigor: boolean;
}

export interface Imagery {
  scene: {
    scene_id: string;
    acquired_on: string;
    synthetic: boolean;
    low_ndvi_threshold: number;
    segmentation_note: string | null;
  } | null;
  zones: ZoneImagery[];
}

export interface ScenarioStatus {
  active: Record<string, Json>[];
  upcoming: Record<string, Json>[];
  /** D014: logged, not ended, no longer applied after a restart. */
  lost: Record<string, Json>[];
}

export type ScenarioRequest =
  | { name: "drought"; start: string; end: string; et0_multiplier?: number }
  | { name: "heavy_rain"; start: string; end: string; total_mm?: number };
