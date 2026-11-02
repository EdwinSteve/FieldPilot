// Dates and times in the plot's local time, in the farmer's words. Pure logic only.
import { plotDay } from "../../lib/format";
import { en } from "../i18n/en";

const HOUR_MS = 3_600_000;
const DAY_MS = 24 * HOUR_MS;

function shifted(iso: string, utcOffsetHours: number): Date {
  return new Date(Date.parse(iso) + utcOffsetHours * HOUR_MS);
}

function clockParts(date: Date): { time: string; meridiem: string } {
  const hours = date.getUTCHours();
  const minutes = String(date.getUTCMinutes()).padStart(2, "0");
  return {
    time: `${hours % 12 === 0 ? 12 : hours % 12}:${minutes}`,
    meridiem: hours < 12 ? en.time.am : en.time.pm,
  };
}

/** "6:00 am" */
export function formatClock(iso: string, utcOffsetHours: number): string {
  const { time, meridiem } = clockParts(shifted(iso, utcOffsetHours));
  return `${time} ${meridiem}`;
}

/** "6:00–9:20 am", or "11:00 am–2:20 pm" across noon. */
export function formatClockRange(startIso: string, endIso: string, utcOffsetHours: number): string {
  const start = clockParts(shifted(startIso, utcOffsetHours));
  const end = clockParts(shifted(endIso, utcOffsetHours));
  if (start.meridiem === end.meridiem) return `${start.time}–${end.time} ${end.meridiem}`;
  return `${start.time} ${start.meridiem}–${end.time} ${end.meridiem}`;
}

/** "Monday, 2 Nov" */
export function formatLongDate(iso: string, utcOffsetHours: number): string {
  const date = shifted(iso, utcOffsetHours);
  const weekday = en.time.weekdays[date.getUTCDay()];
  return `${weekday}, ${date.getUTCDate()} ${en.time.months[date.getUTCMonth()]}`;
}

/** "Monday, 2 Nov · 6:00 am" */
export function formatDateLine(iso: string, utcOffsetHours: number): string {
  return `${formatLongDate(iso, utcOffsetHours)} · ${formatClock(iso, utcOffsetHours)}`;
}

/** "Mon" */
export function shortWeekday(iso: string, utcOffsetHours: number): string {
  return en.time.weekdaysShort[shifted(iso, utcOffsetHours).getUTCDay()] ?? "";
}

/** "28 Oct", from a calendar date. */
export function formatCalendarDate(isoDate: string): string {
  const date = new Date(`${isoDate}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return isoDate;
  return `${date.getUTCDate()} ${en.time.months[date.getUTCMonth()]}`;
}

/** The plot-local hour of the day, 0 to 23. */
export function localHour(iso: string, utcOffsetHours: number): number {
  return shifted(iso, utcOffsetHours).getUTCHours();
}

/** Whole plot-local days from `nowIso` to `iso`: 0 is today, -1 yesterday, 1 tomorrow. */
export function daysFromToday(iso: string, nowIso: string, utcOffsetHours: number): number {
  const day = Date.parse(plotDay(iso, utcOffsetHours));
  const today = Date.parse(plotDay(nowIso, utcOffsetHours));
  return Math.round((day - today) / DAY_MS);
}

/** "Today", "Yesterday", "Tomorrow" or the weekday. */
export function relativeDay(iso: string, nowIso: string, utcOffsetHours: number): string {
  const days = daysFromToday(iso, nowIso, utcOffsetHours);
  if (days === 0) return en.time.today;
  if (days === -1) return en.time.yesterday;
  if (days === 1) return en.time.tomorrow;
  return shortWeekday(iso, utcOffsetHours);
}

/** An instant `days` whole days after `iso`. */
export function plusDays(iso: string, days: number): string {
  return new Date(Date.parse(iso) + days * DAY_MS).toISOString();
}
