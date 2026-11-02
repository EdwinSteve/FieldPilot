// What each screen renders. Screens depend on these types and never on the API.
import type { NormBox } from "../../types/api";
import type { StageState } from "../../lib/stages";
import type { LookedAt } from "../lib/lookedAt";

export interface SoilReading {
  value: number;
  fieldCapacity: number;
}

export interface DecisionLink {
  taskId: number;
  question: string;
}

export interface WeekDay {
  day: string;
  today: boolean;
  water: boolean;
  rain: boolean;
}

export type SoilTone = "needs" | "good";

export interface TodayView {
  dateLine: string;
  greeting: string;
  farmLine: string;
  decision: DecisionLink | null;
  /** Null unless the emergency stop is on. */
  stoppedBanner: string | null;
  zoneId: number;
  statusTitle: string;
  statusDetail: string;
  soil: SoilReading & { display: string; label: string; tone: SoilTone };
  /** `known` is false before the day's check: no figure is not the same as no rain. */
  rain: { mm: number; known: boolean; display: string; label: string };
  plants: { value: string; label: string };
  week: WeekDay[];
}

export interface DecisionView {
  taskId: number;
  zoneName: string;
  question: string;
  why: string;
  soil: SoilReading;
  rainMm: number;
  waterMm: number | null;
  /** False once answered, here or on the dashboard. */
  open: boolean;
  /** True while the emergency stop forbids a yes (D004). */
  stopped: boolean;
}

export type VoiceStatus = "idle" | "starting" | "listening" | "thinking";

/** One question and its answer, as the backend gave them. */
export interface VoiceExchange {
  id: number;
  durationMs: number;
  question: string;
  answer: string | null;
  lookedAt: LookedAt[];
}

export interface TalkChip {
  kind: LookedAt;
  text: string;
}

export interface TalkExchange {
  id: number;
  duration: string;
  /** Spanish, as spoken and answered. */
  question: string;
  answer: string | null;
  chips: TalkChip[];
}

export interface TalkView {
  /** Why asking is off; null when the live model can answer. */
  unavailable: string | null;
  exchanges: TalkExchange[];
  decision: DecisionLink | null;
  waitingCount: number;
}

export interface VoiceControl {
  status: VoiceStatus;
  /** What went wrong with the last question, in the farmer's words. */
  failure: string | null;
  toggle: () => void;
  cancel: () => void;
}

export type UpdateKind = "water" | "satellite" | "report" | "said_no";

export interface UpdateItem {
  id: string;
  kind: UpdateKind;
  title: string;
  time: string;
  href: string;
  unread: boolean;
}

export interface UndoItem {
  taskId: number;
  title: string;
  detail: string;
  timeLeft: string;
  /** Share of the undo window still open, from 0 to 1. */
  remaining: number;
}

export type RareCase =
  | { kind: "recheck"; title: string; detail: string; note: string }
  | { kind: "cut_off"; title: string; detail: string; note: string; zoneHref: string; action: string }
  | { kind: "too_late"; title: string; detail: string };

export interface UpdatesView {
  dateLine: string;
  undo: UndoItem | null;
  undone: boolean;
  rare: RareCase[];
  items: UpdateItem[];
  unreadCount: number;
}

export interface FieldView {
  caption: string;
  headline: string;
  detail: string;
  /** Null when the bare share is unknown (D059). */
  barePct: string | null;
  imageUrl: string;
  imageAlt: string;
  zoneLabel: string;
  zoneArea: NormBox;
  spots: NormBox[];
}

export interface ZoneView {
  name: string;
  caption: string;
  status: string;
  tone: SoilTone;
  soil: SoilReading;
  display: string;
  needsMore: string;
  history: number[];
  historyStart: string;
  historyAlt: string;
  valve: string;
  sensor: string;
}

export type ReportRowKind = "soil" | "rain" | "no_rain" | "done" | "waiting" | "planned" | "satellite";

export interface ReportRow {
  kind: ReportRowKind;
  text: string;
}

export interface ReportView {
  title: string;
  dateLine: string;
  soil: SoilReading;
  rows: ReportRow[];
  original: string;
  saidNo: { detail: string } | null;
  other: { label: string; href: string } | null;
}

export type TaskState =
  | "done"
  | "automatic"
  | "can_undo"
  | "said_no"
  | "needs_you"
  | "planned"
  | "cancelled"
  | "failed";
export type PlanTaskKind = "water" | "report";

export interface PlanTask {
  id: string;
  kind: PlanTaskKind;
  title: string;
  when: string;
  state: TaskState;
  stateLabel: string;
  source: string;
  why: string;
  undoTaskId: number | null;
  decideHref: string | null;
}

export interface PlanDay {
  label: string;
  today: boolean;
  rain: string | null;
  tasks: PlanTask[];
}

export interface PlanStage {
  steps: StageState[];
  now: string;
  next: string | null;
}

export interface PlanView {
  crop: string;
  dayCount: string;
  /** Null while the backend's stage contradicts the crop's age. */
  stage: PlanStage | null;
  days: PlanDay[];
}

export interface StopView {
  stopped: boolean;
  since: string;
  /** End of the watering that keeps running; the stop does not close a valve. */
  runningUntil: string | null;
}

/** Everything the screens need, read fresh from the backend. */
export interface Farm {
  today: TodayView;
  talk: TalkView;
  updates: UpdatesView;
  field: FieldView | null;
  plan: PlanView;
  stop: StopView;
  decision: (taskId: number) => DecisionView | null;
  zone: (zoneId: number) => ZoneView | null;
  report: (reportId: number) => ReportView | null;
  /** Each action resolves true when the backend took it. */
  approve: (taskId: number) => Promise<boolean>;
  reject: (taskId: number, reason?: string) => Promise<boolean>;
  undo: (taskId: number) => Promise<boolean>;
  markAllRead: () => Promise<boolean>;
  setStopped: (stopped: boolean) => Promise<boolean>;
  busy: boolean;
  actionFailed: boolean;
  voice: VoiceControl;
}

export type FarmState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "empty" }
  | { status: "ready"; farm: Farm; stale: boolean };
