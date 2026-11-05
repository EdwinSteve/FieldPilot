import { rainDrops, rainLevel } from "../lib/rainLevel";
import { CLOUD_PATH } from "./Icon";

const DROP_POSITIONS: Record<number, number[]> = {
  0: [],
  1: [12],
  2: [9.5, 14.5],
  3: [7.5, 12, 16.5],
};

interface RainLevelIconProps {
  mm: number;
  size: number;
  /** The cloud's own fill: white on a tinted tile, tinted on a white row. */
  cloudFill?: "surface" | "tint";
}

/** A cloud with 0 to 3 drops. Show the number next to it. */
export function RainLevelIcon({ mm, size, cloudFill = "surface" }: RainLevelIconProps) {
  const drops = rainDrops(rainLevel(mm));
  const fill = cloudFill === "surface" ? "var(--color-surface)" : "var(--color-undo-tint)";
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--color-undo-icon)"
      strokeWidth="1.8"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <path d={CLOUD_PATH} fill={fill} />
      {(DROP_POSITIONS[drops] ?? []).map((x) => (
        <path key={x} d={`M${x} 17.5l-1 3`} strokeWidth="2.2" />
      ))}
      {drops === 0 ? <path d="M5 21L19 5" /> : null}
    </svg>
  );
}
