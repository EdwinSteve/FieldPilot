// Every farmer-facing string. Spanish comes later: keep this file the only source.
import type { RainLevel } from "../lib/rainLevel";
import type { SoilStatus } from "../lib/soilStatus";

function zoneIs(zone: string, status: string): string {
  return `${zone} is ${status === "OK" ? status : status.toLowerCase()}`;
}

export const en = {
  time: {
    am: "am",
    pm: "pm",
    today: "Today",
    yesterday: "Yesterday",
    tomorrow: "Tomorrow",
    weekdays: ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
    weekdaysShort: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
    months: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    greetings: { morning: "Good morning", afternoon: "Good afternoon", evening: "Good evening" },
  },
  names: {
    zone: "Zone",
    maize: "Maize",
    yourField: "Your field",
  },
  autonomy: {
    automatic: "Automatic",
    canUndo: "Can undo",
    needsYou: "Needs you",
  },
  state: {
    loading: "Loading your farm…",
    errorTitle: "I can’t reach the farm right now",
    errorDetail: "I will keep trying.",
    emptyTitle: "No farm yet",
    emptyDetail: "Your farm will appear here once it is set up.",
    actionFailed: "That didn’t work. Please try again.",
    staleData: "I can’t reach the farm. This may be out of date.",
  },
  tabs: {
    label: "Main",
    today: "Today",
    talk: "Talk",
    updates: "Updates",
  },
  back: {
    today: "Back to Today",
    updates: "Back to Updates",
  },
  soil: {
    fullAt: (fieldCapacity: number) => `Full ${fieldCapacity}%`,
    of: (fieldCapacity: number) => `/ ${fieldCapacity}%`,
    unknown: "—",
    tiles: {
      very_dry: "Very dry",
      dry: "Soil · dry",
      ok: "Soil · OK",
      wet: "Soil · wet",
    } satisfies Record<SoilStatus, string>,
    tileUnknown: "Soil",
    status: {
      very_dry: "Very dry",
      dry: "Dry",
      ok: "OK",
      wet: "Wet",
    } satisfies Record<SoilStatus, string>,
    zoneIs,
    noReading: "No soil reading yet",
  },
  rain: {
    levels: {
      none: "none",
      light: "light",
      some: "some",
      heavy: "heavy",
    } satisfies Record<RainLevel, string>,
    tile: (level: string) => `Rain · ${level}`,
    tileUnknown: "Rain",
    unknown: "—",
    amount: (mm: number) => `${mm} mm`,
    expected: "Rain expected in the next 24 h",
    none: "No rain expected",
    notChecked: "Today’s check has not run yet",
  },
  plants: {
    label: "Plants",
    weak: "Weak",
    ok: "OK",
    unknown: "—",
  },
  welcome: {
    logoAlt: "FieldPilot",
    tagline: ["Looks after your field.", "Asks you before big decisions."],
    start: "Start",
  },
  today: {
    stop: "Stop",
    tapToAnswer: "Tap to answer",
    thisWeek: "This week",
    seePlan: "See plan",
    weekDayWater: "water",
    weekDayRain: "rain",
    farmLine: (farm: string, crop: string, day: number) => `${farm} · ${crop}, day ${day}`,
    stoppedDetail: "Tap to see or start again",
  },
  task: {
    water: (zone: string) => `Water ${zone}?`,
    extraWater: (zone: string) => `Extra water for ${zone}?`,
    other: "Do you agree with this?",
  },
  decide: {
    soilNow: "Soil now",
    rainNext24h: "Rain, next 24 h",
    waterToAdd: "Water to add",
    no: "No",
    yes: "Yes",
    whyNot: "Why not?",
    pickOne: "Pick one. It stays in your record.",
    reasons: ["Wait for the rain", "Water costs too much now", "Another reason"],
    skip: "Skip",
    wateringNow: "Watering now",
    wateringDetail: (zone: string, mm: number | null) =>
      mm === null ? `${zone} gets water now.` : `${zone} gets ${mm} mm. You can see it in Updates.`,
    noWater: "OK, no water today",
    noWaterSaved: "Saved with your reason. I will check the soil again tomorrow morning.",
    noWaterSkipped: "I will check the soil again tomorrow morning.",
    backToToday: "Back to Today",
    closedTitle: "Already answered",
    closedDetail: "This decision is no longer waiting for you.",
    stoppedNote: "Watering is stopped. Start again to say yes.",
    holdReasons: {
      emergency_stop_active: "I held this because the emergency stop is on.",
      always_approval_type: "This is always your decision.",
      daily_irrigation_cap_exceeded: "I held this because it goes over the daily limit.",
      rain_forecast_above_limit: "I held this because rain is coming.",
      irrigation_interval_too_short: "I held this because the last watering was too recent.",
      moisture_above_limit: "I held this because the soil is already wet enough.",
      calendar_shift_too_large: "I held this because it moves the date too far.",
      missing_input: "I held this because I am missing some information.",
    } as Record<string, string>,
    holdGeneric: "I want your answer before I do this.",
  },
  talk: {
    title: "Ask me",
    understood: "I understood:",
    lookedAt: "What I looked at",
    agentFirst: "Field",
    agentSecond: "Pilot",
    avatarAlt: "FieldPilot",
    onlyAnswers: "Here I only answer. Watering is decided every morning, and big choices come to you.",
    tapToTalk: "Tap to talk",
    listening: "Listening… tap to send",
    stopAndSend: "Stop and send",
    needsLiveModel: "Talking needs the live model. This demo is running on recorded days.",
    comingSoon: "Talking is not ready yet.",
    decisionsWaiting: (count: number) =>
      count === 1 ? "1 decision waiting" : `${count} decisions waiting`,
  },
  updates: {
    title: "What I did",
    markAllRead: "Mark all read",
    undo: "Undo",
    unread: "New",
    cancelled: "Cancelled. No water used.",
    empty: "Nothing yet. Your first update comes after the morning check.",
    undoTitle: (day: string) => `Extra water, ${day.toLowerCase()}`,
    undoDetail: (zone: string, mm: number | null, time: string) =>
      mm === null ? `${zone} · ${time}` : `${zone} · ${mm} mm · ${time}`,
    watered: (zone: string, mm: number | null) =>
      mm === null ? `Watered ${zone}` : `Watered ${zone} · ${mm} mm`,
    watering: (zone: string, mm: number | null) =>
      mm === null ? `Watering ${zone}` : `Watering ${zone} · ${mm} mm`,
    wateringTime: (day: string, range: string, how: string) => `${day} ${range} · ${how}`,
    youApproved: "You said yes",
    saidNo: "You said no",
    saidNoBecause: (reason: string) =>
      `You said no: ${reason.charAt(0).toLowerCase()}${reason.slice(1)}`,
    saidNoTime: (day: string, time: string, zone: string, mm: number | null) =>
      mm === null ? `${day} ${time} · ${zone}` : `${day} ${time} · ${zone} · ${mm} mm`,
    cancelledRow: (zone: string, mm: number | null) =>
      mm === null ? `You cancelled water for ${zone}` : `You cancelled water · ${zone} · ${mm} mm`,
    plantsWeak: (zone: string) => `Plants weak in ${zone}`,
    satelliteTime: (day: string, time: string) => `${day} ${time} · satellite check`,
    reportTitle: (daysAgo: number, date: string) => {
      if (daysAgo === 0) return "Today’s report";
      if (daysAgo === 1) return "Yesterday’s report";
      return `Report · ${date}`;
    },
    reportTime: (day: string, time: string) => `${day} ${time}`,
    rare: {
      valveClosed: "Valve is now closed",
      undoClosed: "Undo closed",
      recheckTitle: "Extra water didn’t run",
      recheckDetail: (rainMm: number | null) =>
        rainMm === null ? "Things changed before watering" : `Rain is now coming · ${rainMm} mm`,
      recheckNote:
        "I check again right before watering. Things changed, so I will look again in the morning.",
      cutOffTitle: "Watering was cut off",
      cutOffDetail: (zone: string) => `${zone} · amount unknown`,
      cutOffNote: "The system restarted while water was running. It may have kept going.",
      cutOffAction: (zone: string) => `Check ${zone}`,
      tooLateTitle: "Too late to undo",
      tooLateDetail: (zone: string, mm: number | null) =>
        mm === null ? `${zone} · already done` : `${zone} · ${mm} mm already in the soil`,
    },
  },
  field: {
    title: "Field from above",
    caption: (date: string, synthetic: boolean) =>
      synthetic ? `Satellite photo · ${date} · demo image` : `Satellite photo · ${date}`,
    spotsLegend: "Circles show the bare spots",
    askAboutThis: "Ask about this",
    weak: (zone: string) => `Plants in ${zone} look weak`,
    good: (zone: string) => `Plants in ${zone} look good`,
    spots: (count: number) => (count === 1 ? "I found 1 bare spot." : `I found ${count} bare spots.`),
    bareBefore: " About ",
    bareAfter: " of the soil is bare.",
    imageAlt: (zone: string, count: number) =>
      `Satellite photo of the plot. ${zone} has ${count} bare spots marked with circles.`,
    emptyTitle: "No satellite photo yet",
    emptyDetail: "The photo appears here after the next pass.",
  },
  zone: {
    waterInSoil: "Water in the soil",
    zeroPercent: "0%",
    lastDays: "Last 7 days",
    today: "Today",
    valve: "Water valve",
    valveClosed: "Closed",
    valveOpen: (until: string) => `Open until ${until}`,
    sensor: "Soil sensor",
    sensorOk: (time: string) => `OK · ${time}`,
    sensorStale: "No recent reading",
    sensorNone: "No reading yet",
    fewReadings: "Not enough readings yet to draw a line.",
    caption: (areaHa: number, crop: string) => `${areaHa} ha · ${crop.toLowerCase()}`,
    needsMore: (zone: string, points: number) => `${zone} needs about ${points}% more to be full.`,
    isFull: (zone: string) => `${zone} is full.`,
    historyAlt: (first: number, last: number, fieldCapacity: number) =>
      `Soil water went from ${first}% to ${last}%. Full is ${fieldCapacity}%.`,
  },
  report: {
    verified: "Every number was checked against the sensors.",
    original: "Original report (Spanish)",
    saidNo: "After this, you said no",
    saidNoDetail: (time: string, reason: string | null) =>
      reason === null ? time : `${time} · “${reason}”`,
    soil: (zone: string, status: string, value: number, fieldCapacity: number) =>
      `${zoneIs(zone, status)}: ${value}% (full at ${fieldCapacity}%)`,
    noRain: "No rain expected (0 mm)",
    rain: (mm: number) => `Rain expected: ${mm} mm`,
    waiting: (mm: number | null) =>
      mm === null ? "A watering waits for your OK" : `${mm} mm of water waits for your OK`,
    wateringNow: (mm: number | null, until: string | null) => {
      const start = mm === null ? "Watering" : `Watering ${mm} mm`;
      return until === null ? start : `${start} · until ${until}`;
    },
    planned: (mm: number | null, day: string) => {
      const amount = mm === null ? "More water" : `${mm} mm more`;
      return `${amount} ${day.toLowerCase()} · you can undo`;
    },
    satellite: (barePct: number | null) =>
      barePct === null ? "Satellite: weak plants" : `Satellite: weak plants, ${barePct}% bare soil`,
    linkToDay: (day: string, date: string) => `${day} · ${date}`,
    emptyTitle: "No report here",
    emptyDetail: "Reports appear after the morning check.",
  },
  plan: {
    title: "Plan",
    nothingPlanned: "Nothing planned",
    plannedBy: "Planned by",
    undo: "Undo",
    close: "Close",
    answer: "Answer now",
    closeDetails: "Close details",
    taskDetails: "Task details",
    dayCount: (day: number) => `Day ${day}`,
    dayToday: (label: string) => `Today · ${label}`,
    rainExpected: (mm: number) => `Rain ${mm} mm expected`,
    now: (stage: string) => `Now: ${stage}`,
    next: (stage: string) => `Next: ${stage}`,
    stages: {
      sowing: "just sown",
      germination_emergence: "coming up",
      vegetative: "growing leaves",
      flowering: "flowers",
      grain_fill: "filling the ears",
      maturity_harvest: "ready to harvest",
    } as Record<string, string>,
    states: {
      done: "Done",
      said_no: "You said no",
      cancelled: "Cancelled",
      failed: "Didn’t run",
      scheduled: "Planned",
    },
    sources: { water: "Water helper", report: "Report writer", other: "FieldPilot" },
    waterTitle: (zone: string, mm: number | null) =>
      mm === null ? `Water ${zone}` : `Water ${zone} · ${mm} mm`,
    extraTitle: (zone: string, mm: number | null) =>
      mm === null ? `Extra water ${zone}` : `Extra water ${zone} · ${mm} mm`,
    otherTitle: "Other task",
    reportTitle: "Daily report",
    heldForRain: (date: string) => `${date} · held for rain`,
    whyNo: (rainMm: number | null) =>
      rainMm !== null && rainMm > 0
        ? `Rain of ${rainMm} mm was coming, so I asked you. You chose not to water.`
        : "I asked you, and you chose not to water.",
    whyDone: (soilPct: number | null) =>
      soilPct === null
        ? "All safety rules were OK."
        : `The soil was at ${soilPct}%. All safety rules were OK.`,
    whyExtra: (zone: string) => `${zone} is still far from full, so the rest is planned. You can undo it.`,
    whyCancelled: "You cancelled this before it ran.",
    whyWaiting: "I need your answer before I do this.",
    whyFailed: "This did not run. I will look again at the next morning check.",
    whyReport: "Every morning, after my checks, I tell you what I found and planned. Every number is checked.",
  },
  stop: {
    title: "Stop all watering?",
    titleWhileRunning: "Stop new watering?",
    explain: "I will stop adding water and stop changing your plans.",
    explainWhileRunning: (until: string) =>
      `New watering is blocked. Water already running continues until ${until}.`,
    keepsAlerts: "You still get alerts and reports",
    keepsValves: "Open valves can still close",
    confirm: "Yes, stop now",
    cancel: "Cancel",
    stopped: "Watering is stopped",
    stoppedWhileRunning: "New watering is blocked",
    runningUntil: (until: string) => `Water already running continues until ${until}.`,
    since: (time: string, byFarmer: boolean) =>
      byFarmer ? `Since ${time} · by you` : `Since ${time}`,
    noWatering: "No new watering",
    noPlanChanges: "No plan changes",
    valvesCanClose: "Valves can close",
    alertsStillOn: "Alerts and reports still on",
    startAgain: "Start again",
  },
};
