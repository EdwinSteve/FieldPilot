import { useId } from "react";
import { dropFillY, soilFill } from "../lib/soilFill";
import { DROP_PATH } from "./Icon";

interface MoistureDropProps {
  value: number;
  fieldCapacity: number;
  size: number;
  strokeWidth?: number;
}

/** One drop, filled to how much water the soil holds. Show the number next to it. */
export function MoistureDrop({ value, fieldCapacity, size, strokeWidth = 1.6 }: MoistureDropProps) {
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
          fill="var(--color-soil)"
          className="transition-transform duration-400 ease-calm"
          style={{ transform: `translateY(${y}px)` }}
        />
      </g>
      <path d={DROP_PATH} fill="none" stroke="var(--color-needs-icon)" strokeWidth={strokeWidth} />
    </svg>
  );
}
