// Geometry of the moisture drop and the moisture bar. Pure logic only.
import { gaugeFraction } from "../../lib/gauge";

const DROP_BOTTOM = 20;
const DROP_HEIGHT = 17;
/** The bar runs a quarter past full, so the "Full" marker sits at 80% of its width. */
const BAR_SPAN_OF_CAPACITY = 1.25;

/** How full the drop is, from 0 to 1. Above field capacity it stays full. */
export function soilFill(value: number, fieldCapacity: number): number {
  return Math.min(1, gaugeFraction(value, fieldCapacity));
}

/** Top edge of the drop's fill, in its 24×24 viewBox. */
export function dropFillY(fill: number): number {
  return DROP_BOTTOM - DROP_HEIGHT * fill;
}

export interface MoistureBarScale {
  valuePct: number;
  fullPct: number;
}

/** Where the value and the "Full" marker sit on the bar, as CSS percentages. */
export function moistureBarScale(value: number, fieldCapacity: number): MoistureBarScale {
  if (!(fieldCapacity > 0)) return { valuePct: 0, fullPct: 0 };
  const span = fieldCapacity * BAR_SPAN_OF_CAPACITY;
  return {
    valuePct: Math.min(100, Math.max(0, (value / span) * 100)),
    fullPct: 100 / BAR_SPAN_OF_CAPACITY,
  };
}
