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
      <rect
        x="0"
        y={y}
        width="24"
        height={24 - y}
        fill="var(--color-soil)"
        clipPath={`url(#${clipId})`}
      />
      <path d={DROP_PATH} fill="none" stroke="var(--color-needs-icon)" strokeWidth={strokeWidth} />
    </svg>
  );
}
