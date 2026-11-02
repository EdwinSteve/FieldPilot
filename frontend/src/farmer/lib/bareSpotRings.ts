// Rings around the bare spots on the satellite photo. Pure logic only.
import type { NormBox } from "../../types/api";
import { boxRect } from "../../lib/imagery";

export interface Ring {
  cx: number;
  cy: number;
  r: number;
}

/** A little outside the spot, so the ring frames it instead of covering it. */
const RING_MARGIN = 6;

/** One ring per box, in pixels of a width-by-height photo. */
export function bareSpotRings(boxes: readonly NormBox[], width: number, height: number): Ring[] {
  return boxes.map((box) => {
    const rect = boxRect(box);
    const spotWidth = rect.width * width;
    const spotHeight = rect.height * height;
    return {
      cx: (rect.x + rect.width / 2) * width,
      cy: (rect.y + rect.height / 2) * height,
      r: Math.max(spotWidth, spotHeight) / 2 + RING_MARGIN,
    };
  });
}
