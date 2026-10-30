// Geometry of the satellite overlay and the NDVI scale. Pure logic only.
import type { NormBox } from "../types/api";

export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

/** A normalized box as SVG rect attributes. */
export function boxRect(box: NormBox): Rect {
  return { x: box.x1, y: box.y1, width: box.x2 - box.x1, height: box.y2 - box.y1 };
}

/** Where an NDVI value sits on the [-1, 1] scale, as a 0-100 percent. Null stays null. */
export function ndviPosition(ndviMean: number | null): number | null {
  if (ndviMean === null) return null;
  return Math.min(100, Math.max(0, ((ndviMean + 1) / 2) * 100));
}
