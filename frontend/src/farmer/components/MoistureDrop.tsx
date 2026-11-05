import { useId } from "react";
import { dropFillY, soilFill } from "../lib/soilFill";
import { soilStatus } from "../lib/soilStatus";
import { soilLevel, type Level } from "../lib/statusLevel";
import { DROP_PATH } from "./Icon";
import { LEVEL_COLOUR } from "./levelStyle";

const DROP_FILLS: Record<Level, string> = {
  good: "var(--color-leaf)",
  watch: "var(--color-soil)",
  bad: "var(--color-bad)",
  info: "var(--color-undo)",
  neutral: "var(--color-divider)",
};

interface MoistureDropProps {
  value: number;
  fieldCapacity: number;
  size: number;
  strokeWidth?: number;
  /** Given when the reading is missing; otherwise it follows the value. */
  level?: Level;
}

/** One drop, filled to how much water the soil holds. Show the number next to it. */
export function MoistureDrop({
  value,
  fieldCapacity,
  size,
  strokeWidth = 1.6,
  level = soilLevel(soilStatus(value, fieldCapacity)),
}: MoistureDropProps) {
  const clipId = useId();
  const y = dropFillY(soilFill(value, fieldCapacity));
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <defs>
        <clipPath id={clipId}>
          <path d={DROP_PATH} />
        </clipPath>
      </defs>
      <g clipPath={`url(#${clipId})`}>
        {/* Moved, not resized, so a new reading can ease to its level. */}
        <rect
          width="24"
          height="24"
          fill={DROP_FILLS[level]}
          className="transition-transform duration-400 ease-calm"
          style={{ transform: `translateY(${y}px)` }}
        />
      </g>
      <path d={DROP_PATH} fill="none" stroke={LEVEL_COLOUR[level]} strokeWidth={strokeWidth} />
    </svg>
  );
}
