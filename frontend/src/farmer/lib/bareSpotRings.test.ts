import { describe, expect, it } from "vitest";
import { bareSpotRings } from "./bareSpotRings";

describe("bareSpotRings", () => {
  it("centres a ring on the box, in photo pixels", () => {
    const box = { x1: 376 / 512, y1: 126 / 256, x2: 464 / 512, y2: 214 / 256 };
    expect(bareSpotRings([box], 512, 256)).toEqual([{ cx: 420, cy: 170, r: 50 }]);
  });

  it("uses the longer side for a box that is not square", () => {
    const [ring] = bareSpotRings([{ x1: 0, y1: 0, x2: 0.5, y2: 0.1 }], 100, 100);
    expect(ring?.r).toBe(31);
  });

  it("draws nothing without boxes", () => {
    expect(bareSpotRings([], 512, 256)).toEqual([]);
  });
});
