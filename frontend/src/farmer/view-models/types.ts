// What each screen renders. Screens depend on these types and never on the API.
import type { NormBox } from "../../types/api";
import type { StageState } from "../../lib/stages";
import type { ActionFailure } from "../lib/actionFailure";
import type { ApprovalOutcome } from "../lib/approvalOutcome";
import type { LookedAt } from "../lib/lookedAt";
import type { TrendDirection } from "../lib/soilTrend";
import type { Level } from "../lib/statusLevel";

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

export interface TodayView {
  dateLine: string;
  greeting: string;
  farmLine: string;
  decision: DecisionLink | null;
  /** Null unless the emergency stop is on. */
  stoppedBanner: string | null;
  zoneId: number;
  /** The worst of what the tiles judge: the answer at a glance. */
  status: Level;
  statusLabel: string;
  statusTitle: string;
  statusDetail: string;
  /** `display` and `ofFull` read together: "20" "of 32%". */
  soil: SoilReading & {
    display: string;
    ofFull: string | null;
    label: string;
    level: Level;
    /** Null until there is a reading from about a day before. */
    trend: TrendDirection | null;
  };
  /** `known` is false before the day's check: no figure is not the same as no rain. */
  rain: { mm: number; known: boolean; display: string; label: string };
  plants: { value: string; label: string; level: Level };
  recent: UpdateItem[];
  week: WeekDay[];
}

export interface DecisionView {
  taskId: number;
  zoneName: string;
  question: string;
  why: string;
  soil: SoilReading;
  percentFull: string;
  rainMm: number;
  waterMm: number | null;
  /** False once answered, here or on the dashboard. */
  open: boolean;
  /** True while the emergency stop forbids a yes (D004). */
  stopped: boolean;
}

export type TalkStatus = "idle" | "starting" | "listening" | "thinking";

/** One question and its answer, as the backend gave them. */
export interface ChatExchange {
  id: number;
  /** How long the recording ran; null for a typed question. */
  durationMs: number | null;
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
  /** Null for a typed question. */
  duration: string | null;
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

export interface TalkControl {
  status: TalkStatus;
  /** What went wrong with the last question, in the farmer's words. */
  failure: string | null;
  /** The typed question on its way, shown before its answer arrives. */
  pendingQuestion: string | null;
  draft: string;
  setDraft: (text: string) => void;
  sendDraft: () => void;
  ask: (question: string) => void;
  toggleMic: () => void;
  cancel: () => void;
}

export type UpdateKind =
  | "water"
  | "undo"
  | "satellite"
  | "report"
  | "said_no"
  | "problem"
  | "alert";

export interface UpdateItem {
  id: string;
  kind: UpdateKind;
  title: string;
  /** Set when the words are the backend's own, not this app's. */
  lang?: "es";
  /** The day it is filed under on Updates: "Today", "Mon 2 Nov". */
  group: string;
  /** With its day, "Today 6:00 am", for a list without day headings. */
  time: string;
  /** Without the day when the heading already says it. */
  timeInDay: string;
  /** Null when there is nothing more to open. */
  href: string | null;
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
  /** What the last undo did, while it is still news. */
  undone: string | null;
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
  level: Level;
  soil: SoilReading & { level: Level };
  display: string;
  /** "About 63% full": the number in everyday words. */
  percentFull: string | null;
  /** Null until there is a reading from about a day before. */
  trend: string | null;
  needsMore: string;
  history: number[];
  historyStart: string;
  historyAlt: string;
  valve: string;
  valveLevel: Level;
  sensor: string;
  sensorLevel: Level;
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
  /** What runs first once the farmer starts again; null when nothing is planned. */
  nextWatering: string | null;
}

/** Everything the screens need, read fresh from the backend. */
export interface Farm {
  today: TodayView;
  chat: TalkView;
  updates: UpdatesView;
  field: FieldView | null;
  plan: PlanView;
  stop: StopView;
  decision: (taskId: number) => DecisionView | null;
  zone: (zoneId: number) => ZoneView | null;
  report: (reportId: number) => ReportView | null;
  /** Each action resolves true when the backend took it. */
  /** What the yes led to, or null when the backend could not be reached. */
  approve: (taskId: number) => Promise<ApprovalOutcome | null>;
  reject: (taskId: number, reason?: string) => Promise<boolean>;
  undo: (taskId: number) => Promise<boolean>;
  markAllRead: () => Promise<boolean>;
  setStopped: (stopped: boolean) => Promise<boolean>;
  busy: boolean;
  /** Why the last action failed, while the notice is up. */
  actionFailure: ActionFailure | null;
  talk: TalkControl;
}

export type FarmState =
  | { status: "loading" }
  | { status: "error"; retry: () => void; retrying: boolean; lastTried: string }
  | { status: "empty" }
  | {
      status: "ready";
      farm: Farm;
      stale: boolean;
      /** How old the farm on screen is, "just now" or "4 min ago"; null when unknown. */
      age: string | null;
    };
