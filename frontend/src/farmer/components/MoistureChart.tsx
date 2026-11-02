import { toPoints } from "../../lib/chart";
import { en } from "../i18n/en";
import type { Level } from "../lib/statusLevel";
import { LEVEL_COLOUR } from "./levelStyle";

const WIDTH = 320;
const HEIGHT = 112;
const MARGIN_X = 10;
const TOP = 21;
const PLOT_HEIGHT = 84;

interface MoistureChartProps {
  values: number[];
  fieldCapacity: number;
  startLabel: string;
  alt: string;
  level: Level;
}

/**
 * Soil water over the last days, under a dashed "Full" line. Needs two readings to draw.
 * The labels sit outside the SVG: inside it they would shrink below 15 px on a small phone.
 */
export function MoistureChart({ values, fieldCapacity, startLabel, alt, level }: MoistureChartProps) {
  if (values.length < 2) {
    return <p className="text-small text-ink-3">{en.zone.fewReadings}</p>;
  }
  // The plot's top is "Full", its bottom the driest reading.
  const range = { min: Math.min(...values), max: Math.max(fieldCapacity, ...values) };
  const points = toPoints(values, WIDTH - 2 * MARGIN_X, PLOT_HEIGHT, range);
  const last = points.split(" ").at(-1)?.split(",").map(Number) ?? [0, 0];
  return (
    <div className="relative">
      <p className="sr-only">{alt}</p>
      <span className="absolute top-0 right-1 text-caption font-bold text-primary">
        {en.soil.fullAt(fieldCapacity)}
      </span>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} aria-hidden="true" className="h-auto w-full">
        <line
          x1="0"
          y1={TOP}
          x2={WIDTH}
          y2={TOP}
          stroke="var(--color-primary)"
          strokeWidth="2"
          strokeDasharray="6 5"
        />
        <g transform={`translate(${MARGIN_X} ${TOP})`}>
          <polyline
            points={points}
            fill="none"
            stroke={LEVEL_COLOUR[level]}
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx={last[0]} cy={last[1]} r="6" fill={LEVEL_COLOUR[level]} />
        </g>
      </svg>
      <div className="flex justify-between px-2.5 text-caption">
        <span className="text-ink-3">{startLabel}</span>
        <span className="font-bold text-ink">{en.zone.today}</span>
      </div>
    </div>
  );
}
