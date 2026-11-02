// The one place that says what each level looks like. Colour always comes with an icon or a word.
import type { Level } from "../lib/statusLevel";
import type { ChipTone } from "./Chip";
import type { IconName } from "./Icon";
import type { CircleTone } from "./IconCircle";

export const LEVEL_TILE: Record<Level, string> = {
  good: "bg-tint text-primary-hover",
  watch: "bg-needs-tint text-needs-text",
  bad: "bg-bad-tint text-bad-text",
  info: "bg-undo-tint text-undo-text",
  neutral: "bg-divider text-ink-2",
};

export const LEVEL_TEXT: Record<Level, string> = {
  good: "text-primary",
  watch: "text-needs-text",
  bad: "text-bad-text",
  info: "text-undo-text",
  neutral: "text-ink-2",
};

export const LEVEL_FILL: Record<Level, string> = {
  good: "bg-field",
  watch: "bg-needs",
  bad: "bg-bad",
  info: "bg-undo",
  neutral: "bg-ink-3",
};

/** For SVG, where a class cannot set the stroke by level. */
export const LEVEL_COLOUR: Record<Level, string> = {
  good: "var(--color-field)",
  watch: "var(--color-needs)",
  bad: "var(--color-bad)",
  info: "var(--color-undo)",
  neutral: "var(--color-ink-3)",
};

export const LEVEL_CHIP: Record<Level, ChipTone> = {
  good: "good",
  watch: "needs",
  bad: "bad",
  info: "undo",
  neutral: "neutral",
};

export const LEVEL_CIRCLE: Record<Level, CircleTone> = {
  good: "good",
  watch: "needs",
  bad: "stop",
  info: "undo",
  neutral: "neutral",
};

/** Routine rows stay white, so the ones that need a look stand out. */
export function isTinted(level: Level): boolean {
  return level === "watch" || level === "bad" || level === "info";
}

/** The fill of a row of this level. */
export function levelFill(level: Level): string {
  return isTinted(level) ? LEVEL_TILE[level] : "bg-surface text-ink";
}

/** A whole row as a card of its level. Titles keep ink, so they stay easy to read. */
export function levelCard(level: Level): string {
  return `rounded-tile px-3 py-3 ${levelFill(level)}`;
}

/** Null where the level judges nothing, so an icon would claim too much. */
export const LEVEL_ICON: Record<Level, IconName | null> = {
  good: "check",
  watch: "clock",
  bad: "warning",
  info: null,
  neutral: null,
};
