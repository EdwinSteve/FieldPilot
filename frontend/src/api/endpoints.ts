// One function per backend endpoint (architecture §7). No logic beyond the call.
import type {
  Crop,
  ChatAnswer,
  Clock,
  ClockChange,
  Cycle,
  DailyCycleResult,
  EmergencyStop,
  Imagery,
  Weather,
  LogEvent,
  Notification,
  Plot,
  Policy,
  Report,
  RevertResult,
  ScenarioRequest,
  ScenarioStatus,
  SensorReadings,
  Task,
  TaskStatus,
  TickResult,
  VoiceAnswer,
  Zone,
} from "../types/api";
import { apiUrl, getJson, postBytes, postJson } from "./client";

export const api = {
  plots: () => getJson<Plot[]>("/plots"),
  zones: (plotId: number) => getJson<Zone[]>(`/plots/${plotId}/zones`),
  imagery: (plotId: number) => getJson<Imagery>(`/plots/${plotId}/imagery`),
  weather: (plotId: number) => getJson<Weather>(`/plots/${plotId}/weather`),
  imageryImageUrl: (plotId: number) => apiUrl(`/plots/${plotId}/imagery/image`),
  readings: (zoneId: number, limit = 200) =>
    getJson<SensorReadings[]>(`/readings?zone_id=${zoneId}&limit=${limit}`),
  cycles: () => getJson<Cycle[]>("/cycles"),
  crop: (name: string) => getJson<Crop>(`/crops/${encodeURIComponent(name)}`),

  tasks: (status?: TaskStatus) => getJson<Task[]>(status ? `/tasks?status=${status}` : "/tasks"),
  approve: (taskId: number) => postJson<Task>(`/tasks/${taskId}/approve`),
  reject: (taskId: number, reason?: string) =>
    postJson<Task>(`/tasks/${taskId}/reject`, reason ? { reason } : undefined),
  done: (taskId: number) => postJson<Task>(`/tasks/${taskId}/done`),
  revert: (taskId: number) => postJson<RevertResult>(`/tasks/${taskId}/revert`),

  events: (params: { kind?: string; taskId?: number; limit?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.kind) query.set("kind", params.kind);
    if (params.taskId !== undefined) query.set("task_id", String(params.taskId));
    query.set("limit", String(params.limit ?? 500));
    return getJson<LogEvent[]>(`/events?${query.toString()}`);
  },
  notifications: (unreadOnly = false) =>
    getJson<Notification[]>(`/notifications?unread_only=${unreadOnly}`),
  markRead: (id: number) => postJson<Notification>(`/notifications/${id}/read`),
  reports: () => getJson<Report[]>("/reports"),

  chat: (plotId: number, question: string) =>
    postJson<ChatAnswer>("/agent/chat", { plot_id: plotId, question }),
  chatVoice: (plotId: number, wav: Blob) =>
    postBytes<VoiceAnswer>(`/agent/chat/voice?plot_id=${plotId}`, wav, "audio/wav"),
  dailyCycle: (plotId: number) =>
    postJson<DailyCycleResult>("/agent/daily-cycle", { plot_id: plotId }),

  clock: () => getJson<Clock>("/clock"),
  changeClock: (change: ClockChange) => postJson<Clock>("/clock", change),
  tick: () => postJson<TickResult>("/simulation/tick"),
  simulationStatus: () => getJson<ScenarioStatus>("/simulation/status"),
  injectScenario: (scenario: ScenarioRequest) =>
    postJson<Record<string, unknown>>("/simulation/scenarios", scenario),
  emergencyStop: () => getJson<EmergencyStop>("/emergency-stop"),
  setEmergencyStop: (active: boolean) => postJson<EmergencyStop>("/emergency-stop", { active }),
  policy: () => getJson<Policy>("/autonomy/policy"),
};
