import type { ReactNode } from "react";
import type { Level } from "../lib/statusLevel";
import { LEVEL_CIRCLE, LEVEL_TEXT, isTinted } from "./levelStyle";

export type CircleTone = "needs" | "needsSolid" | "undo" | "good" | "neutral" | "stop";
type CircleSize =
  | "small"
  | "row"
  | "medium"
  | "large"
  | "welcome"
  | "wide"
  | "tall"
  | "hero"
  | "stop";

const TONES: Record<CircleTone, string> = {
  needs: "bg-needs-tint text-needs-icon",
  needsSolid: "bg-needs text-surface",
  undo: "bg-undo-tint text-undo-icon",
  good: "bg-tint text-primary",
  neutral: "bg-divider text-ink-2",
  stop: "bg-stop-tint text-stop",
};

const SIZES: Record<CircleSize, string> = {
  small: "size-10",
  row: "size-11.5",
  medium: "size-12",
  large: "size-13.5",
  welcome: "size-14",
  wide: "size-15",
  tall: "size-18",
  hero: "size-30",
  stop: "size-33",
};

interface CardIconProps {
  level: Level;
  size?: CircleSize;
  children: ReactNode;
}

interface IconCircleProps {
  tone: CircleTone;
  size: CircleSize;
  children: ReactNode;
}

/** An icon on a row: white on a tinted card, tinted on a white one. */
export function CardIcon({ level, size = "medium", children }: CardIconProps) {
  if (!isTinted(level)) {
    return (
      <IconCircle tone={LEVEL_CIRCLE[level]} size={size}>
        {children}
      </IconCircle>
    );
  }
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded-full bg-surface ${LEVEL_TEXT[level]} ${SIZES[size]}`}
    >
      {children}
    </span>
  );
}

export function IconCircle({ tone, size, children }: IconCircleProps) {
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded-full ${TONES[tone]} ${SIZES[size]}`}
    >
      {children}
    </span>
  );
}
