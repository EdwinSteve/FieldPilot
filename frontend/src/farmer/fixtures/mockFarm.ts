// Phase 1 only: the v3 artboards as typed view-models, so screens render with no backend.
// Text here is sample data, not UI copy; the view-models build the real text from i18n.
import { useMemo, useState } from "react";
import { api } from "../../api/endpoints";
import type { NormBox } from "../../types/api";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import type {
  DecisionView,
  Farm,
  FieldView,
  PlanView,
  RareCase,
  ReportView,
  TalkView,
  TodayView,
  UpdatesView,
  ZoneView,
} from "../view-models/types";

const PLOT_ID = 1;
const ZONE_ID = 1;
const HELD_TASK_ID = 1;
const EXTRA_TASK_ID = 3;
const FIELD_CAPACITY = 32;

const SOIL_DAY_1 = { value: 20, fieldCapacity: FIELD_CAPACITY };
const SOIL_DAY_2 = { value: 16.7, fieldCapacity: FIELD_CAPACITY };

const today: TodayView = {
  dateLine: "Monday, 2 Nov · 6:00 am",
  greeting: "Good morning",
  farmLine: "Finca demo · Maize, day 32",
  decision: { taskId: HELD_TASK_ID, question: "Water Zone 2?" },
  stopped: false,
  zoneId: ZONE_ID,
  statusTitle: "Zone 2 is dry",
  statusDetail: "Rain expected in the next 24 h",
  soil: { ...SOIL_DAY_1, label: "Soil · dry" },
  rain: { mm: 12, label: "Rain · some" },
  plants: { value: "Weak", label: "Plants" },
  week: [
    { day: "Mon", today: true, water: true, rain: false },
    { day: "Tue", today: false, water: false, rain: true },
    { day: "Wed", today: false, water: false, rain: false },
    { day: "Thu", today: false, water: false, rain: false },
    { day: "Fri", today: false, water: false, rain: false },
    { day: "Sat", today: false, water: false, rain: false },
    { day: "Sun", today: false, water: false, rain: false },
  ],
};

const decision: DecisionView = {
  taskId: HELD_TASK_ID,
  zoneName: "Zone 2",
  question: "Water Zone 2?",
  why: "I held this because rain is coming.",
  soil: SOIL_DAY_1,
  rainMm: 12,
  waterMm: 20,
};

const talk: TalkView = {
  exchange: {
    duration: "0:04",
    question: "Does the maize in zone two need water?",
    answer: "Yes, Zone 2 is dry. It needs about 12% more water.",
    detail: "But rain is coming, so I asked you first.",
    chips: [
      { kind: "soil", text: "Soil 20% · full at 32%" },
      { kind: "rain", text: "Rain 12 mm · 24 h" },
    ],
  },
  decision: { taskId: HELD_TASK_ID, question: "Water Zone 2?" },
  waitingCount: 1,
};

const RARE_CASES: RareCase[] = [
  {
    kind: "recheck",
    title: "Extra water didn’t run",
    detail: "Rain is now coming · 8 mm",
    note: "I check again right before watering. Things changed, so I will decide again in the morning.",
  },
  {
    kind: "cut_off",
    title: "Watering was cut off",
    detail: "Zone 2 · amount unknown",
    note: "The system restarted while water was running. It may have kept going.",
    zoneHref: hrefOf({ screen: "zone", zoneId: ZONE_ID }),
    action: "Check Zone 2",
  },
  {
    kind: "too_late",
    title: "Too late to undo",
    detail: "Zone 2 · 20 mm already in the soil",
  },
];

const updates: UpdatesView = {
  dateLine: "Tuesday, 3 Nov · 9:30 am",
  undo: {
    taskId: EXTRA_TASK_ID,
    title: "Extra water, tomorrow",
    detail: "Zone 2 · 20 mm · 6 am",
    timeLeft: "2 h 35 min",
    remaining: 155 / 360,
  },
  undone: false,
  rare: [],
  items: [
    {
      id: "water-2",
      kind: "water",
      title: "Watered Zone 2 · 20 mm",
      time: "Today 6:00–9:20 am · Automatic",
      href: hrefOf({ screen: "plan" }),
      unread: true,
    },
    {
      id: "satellite-2",
      kind: "satellite",
      title: "Plants weak in Zone 2",
      time: "Today 6:05 am · satellite check",
      href: hrefOf({ screen: "field" }),
      unread: false,
    },
    {
      id: "report-2",
      kind: "report",
      title: "Today’s report",
      time: "Today 6:05 am",
      href: hrefOf({ screen: "report", reportId: 2 }),
      unread: false,
    },
    {
      id: "no-1",
      kind: "said_no",
      title: "You said no: wait for rain",
      time: "Mon 6:12 am · Zone 2 · 20 mm",
      href: hrefOf({ screen: "plan" }),
      unread: false,
    },
    {
      id: "report-1",
      kind: "report",
      title: "Yesterday’s report",
      time: "Mon 6:05 am",
      href: hrefOf({ screen: "report", reportId: 1 }),
      unread: false,
    },
  ],
};

/** The three SAM boxes of the demo scene, from generate_demo_scene.py's patches. */
const BARE_SPOTS: NormBox[] = [
  { x1: 292 / 512, y1: 32 / 256, x2: 368 / 512, y2: 108 / 256 },
  { x1: 375 / 512, y1: 125 / 256, x2: 465 / 512, y2: 215 / 256 },
  { x1: 270 / 512, y1: 160 / 256, x2: 330 / 512, y2: 220 / 256 },
];

const field: FieldView = {
  caption: "Satellite photo · 28 Oct · demo image",
  headline: "Plants in Zone 2 look weak",
  detail: "I found 3 bare spots. About ",
  barePct: "25%",
  detailEnd: " of the soil is bare.",
  imageUrl: api.imageryImageUrl(PLOT_ID),
  imageAlt: "Satellite photo of the plot. Zone 2 has three bare spots.",
  zoneLabel: "Zone 2",
  zoneArea: { x1: 0.5, y1: 0, x2: 1, y2: 1 },
  spots: BARE_SPOTS,
};

const zone: ZoneView = {
  name: "Zone 2",
  caption: "0.5 ha · maize",
  status: "Dry",
  soil: SOIL_DAY_1,
  needsMore: "Zone 2 needs about 12% more to be full.",
  history: [26, 25, 24, 23, 22, 21, 20],
  historyStart: "Tue",
  historyAlt: "Soil water went down from 26% to 20% over 7 days. Full is 32%.",
  valve: "Closed",
  sensor: "OK · 6:00 am",
};

const reportDay2: ReportView = {
  title: "Today’s report",
  dateLine: "Tuesday, 3 Nov · 6:05 am",
  soil: SOIL_DAY_2,
  rows: [
    { kind: "soil", text: "Zone 2 is very dry: 16.7% (full at 32%)" },
    { kind: "no_rain", text: "No rain expected (0 mm)" },
    { kind: "done", text: "Watering 20 mm now · until 9:20 am" },
    { kind: "planned", text: "20 mm more tomorrow · you can undo" },
    { kind: "satellite", text: "Satellite: weak plants, 25% bare soil" },
  ],
  original:
    "La Zona 2 está seca con una humedad del 16,7 % frente a una capacidad de campo del 32,0 %, en siembra con 0 mm de lluvia prevista y 0 GDD acumulados. La imagen muestra vigor bajo en la Zona 2 con un 21,2 % de NDVI bajo y aproximadamente un 25,3 % de suelo desnudo. Se ejecutó el riego programado y queda programado un riego extra.",
  saidNo: null,
  other: { label: "Yesterday · Mon 2 Nov", href: hrefOf({ screen: "report", reportId: 1 }) },
};

const reportDay1: ReportView = {
  title: "Yesterday’s report",
  dateLine: "Monday, 2 Nov · 6:05 am",
  soil: SOIL_DAY_1,
  rows: [
    { kind: "soil", text: "Zone 2 is dry: 20% (full at 32%)" },
    { kind: "rain", text: "Rain expected: 12 mm" },
    { kind: "waiting", text: "20 mm of water waits for your OK" },
    { kind: "satellite", text: "Satellite: weak plants, 25% bare soil" },
  ],
  original:
    "Zona 2 está seca con humedad de 20,0 % muy por debajo de la capacidad de campo de 32,0 %, en etapa de siembra con 0,0 GDD acumulados y lluvia prevista de 12 mm. La imagen muestra vigor bajo en Zona 2 con 21,2 % de área de bajo NDVI y aproximadamente 25,3 % de suelo desnudo. El riego propuesto espera la aprobación del agricultor.",
  saidNo: { detail: "6:12 am · “Wait for the rain”" },
  other: { label: "Today · Tue 3 Nov", href: hrefOf({ screen: "report", reportId: 2 }) },
};

const plan: PlanView = {
  crop: "Maize",
  dayCount: "Day 33",
  stage: null,
  days: [
    {
      label: "Mon 2",
      today: false,
      rain: "Rain 12 mm expected",
      tasks: [
        {
          id: "water-1",
          kind: "water",
          title: "Water Zone 2 · 20 mm",
          when: "Mon 2 Nov · held for rain",
          state: "said_no",
          stateLabel: "You said no",
          source: "Water helper",
          why: "Rain of 12 mm was coming, so I asked you. You chose to wait for the rain.",
          undoTaskId: null,
        },
      ],
    },
    {
      label: "Today · Tue 3",
      today: true,
      rain: null,
      tasks: [
        {
          id: "water-2",
          kind: "water",
          title: "Watered Zone 2 · 20 mm",
          when: "Today 6:00–9:20 am",
          state: "done",
          stateLabel: "Done",
          source: "Water helper",
          why: "The rain did not come and the soil fell to 16.7%. All safety rules were OK.",
          undoTaskId: null,
        },
        {
          id: "report-2",
          kind: "report",
          title: "Daily report",
          when: "Today 6:05 am",
          state: "automatic",
          stateLabel: en.autonomy.automatic,
          source: "Report writer",
          why: "Every morning, after my checks, I tell you what I found and planned. Every number is checked.",
          undoTaskId: null,
        },
      ],
    },
    {
      label: "Wed 4",
      today: false,
      rain: null,
      tasks: [
        {
          id: "water-3",
          kind: "water",
          title: "Extra water Zone 2 · 20 mm",
          when: "Wed 4 Nov · 6:00 am",
          state: "can_undo",
          stateLabel: en.autonomy.canUndo,
          source: "Water helper",
          why: "Zone 2 is still far from full. The limit is 20 mm a day, so the rest is planned for tomorrow.",
          undoTaskId: EXTRA_TASK_ID,
        },
      ],
    },
    { label: "Thu 5", today: false, rain: null, tasks: [] },
  ],
};

const flagOn = (name: string) => new URLSearchParams(window.location.search).has(name);

/** The real farm hook will return this same shape. `?rare` and `?running` show those cases. */
export function useMockFarm(): Farm {
  const [stopped, setStopped] = useState(false);
  const [undone, setUndone] = useState(false);
  const [allRead, setAllRead] = useState(false);

  return useMemo(() => {
    const items = updates.items.map((item) => ({ ...item, unread: item.unread && !allRead }));
    return {
      today: { ...today, stopped },
      talk,
      updates: { ...updates, undone, items, rare: flagOn("rare") ? RARE_CASES : [] },
      field,
      plan,
      stop: {
        stopped,
        since: "Since 7:12 am · by you",
        runningUntil: flagOn("running") ? "9:20 am" : null,
      },
      decision: (taskId) => (taskId === HELD_TASK_ID ? decision : null),
      zone: (zoneId) => (zoneId === ZONE_ID ? zone : null),
      report: (reportId) => (reportId === 1 ? reportDay1 : reportId === 2 ? reportDay2 : null),
      approve: () => Promise.resolve(),
      reject: () => Promise.resolve(),
      undo: () => {
        setUndone(true);
        return Promise.resolve();
      },
      markAllRead: () => {
        setAllRead(true);
        return Promise.resolve();
      },
      setStopped: (next) => {
        setStopped(next);
        return Promise.resolve();
      },
    };
  }, [stopped, undone, allRead]);
}
