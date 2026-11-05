import { describe, expect, it } from "vitest";
import { areaHectares, hectaresText, inColombia, middleOf, outlineProblem } from "./farmOutline";

/** About 200 m × 200 m near La Plata, Huila: 4 ha. */
const square = [
  { lat: 2.39, lng: -75.89 },
  { lat: 2.39, lng: -75.888_203 },
  { lat: 2.391_809, lng: -75.888_203 },
  { lat: 2.391_809, lng: -75.89 },
];

describe("areaHectares", () => {
  it("measures a farm in hectares", () => {
    expect(areaHectares(square)).toBeCloseTo(4, 1);
  });

  it("is the same whichever way the corners go", () => {
    expect(areaHectares(square.toReversed())).toBeCloseTo(areaHectares(square), 6);
  });

  it("is zero under three points", () => {
    expect(areaHectares(square.slice(0, 2))).toBe(0);
  });
});

describe("middleOf", () => {
  it("averages the corners", () => {
    const middle = middleOf(square);
    expect(middle?.lat).toBeCloseTo(2.390_904, 5);
    expect(middle?.lng).toBeCloseTo(-75.889_101, 5);
  });

  it("has no middle without points", () => {
    expect(middleOf([])).toBeNull();
  });
});

describe("outlineProblem", () => {
  it("wants three points or more", () => {
    expect(outlineProblem(square.slice(0, 2))).toBe("too_few");
  });

  it("wants the farm in Colombia", () => {
    expect(inColombia({ lat: 4.6, lng: -74.08 })).toBe(true);
    expect(outlineProblem(square.map((p) => ({ ...p, lng: p.lng + 20 })))).toBe("outside_colombia");
  });

  it("refuses more than 1000 ha", () => {
    const huge = [
      { lat: 2, lng: -76 },
      { lat: 2, lng: -75.5 },
      { lat: 2.5, lng: -75.5 },
    ];
    expect(outlineProblem(huge)).toBe("too_large");
  });

  it("accepts a real farm", () => {
    expect(outlineProblem(square)).toBeNull();
  });
});

describe("hectaresText", () => {
  it("keeps two places under a hectare and one above", () => {
    expect(hectaresText(0.254)).toBe("0.25 ha");
    expect(hectaresText(3.46)).toBe("3.5 ha");
    expect(hectaresText(4)).toBe("4 ha");
  });
});
