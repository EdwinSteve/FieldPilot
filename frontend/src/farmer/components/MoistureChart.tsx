import { toPoints } from "../../lib/chart";
import { en } from "../i18n/en";
import type { Level } from "../lib/statusLevel";
import { LEVEL_COLOUR } from "./levelStyle";

const WIDTH = 320;
const HEIGHT = 130;
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

/** Soil water over the last days, under a dashed "Full" line. Needs two readings to draw. */
export function MoistureChart({ values, fieldCapacity, startLabel, alt, level }: MoistureChartProps) {
  if (values.length < 2) {
    return <p className="text-small text-ink-3">{en.zone.fewReadings}</p>;
  }
  // The plot's top is "Full", its bottom the driest reading.
  const range = { min: Math.min(...values), max: Math.max(fieldCapacity, ...values) };
  const points = toPoints(values, WIDTH - 2 * MARGIN_X, PLOT_HEIGHT, range);
  const last = points.split(" ").at(-1)?.split(",").map(Number) ?? [0, 0];
  return (
    <>
      <p className="sr-only">{alt}</p>
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
        <text
          x={WIDTH - 4}
          y="14"
          textAnchor="end"
          fontSize="15"
          fontWeight="700"
          fill="var(--color-primary)"
        >
          {en.soil.fullAt(fieldCapacity)}
        </text>
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
        <text x={MARGIN_X} y="126" fontSize="15" fill="var(--color-ink-3)">
          {startLabel}
        </text>
        <text
          x={WIDTH - MARGIN_X}
          y="126"
          textAnchor="end"
          fontSize="15"
          fontWeight="700"
          fill="var(--color-ink)"
        >
          {en.zone.today}
        </text>
      </svg>
    </>
  );
}
