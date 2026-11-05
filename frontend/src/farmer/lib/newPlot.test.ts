import { describe, expect, it } from "vitest";
import { hasProblem, newPlot, plotProblems } from "./newPlot";

const square = [
  { lat: 2.39, lng: -75.89 },
  { lat: 2.39, lng: -75.888_203 },
  { lat: 2.391_809, lng: -75.888_203 },
  { lat: 2.391_809, lng: -75.89 },
];

describe("plotProblems", () => {
  it("finds nothing in a complete form", () => {
    expect(hasProblem(plotProblems(square, "La Esperanza", "La Plata", "Huila"))).toBe(false);
  });

  it("names each missing part", () => {
    expect(plotProblems(square.slice(0, 1), " ", "L", "")).toEqual({
      outline: "too_few",
      name: "missing",
      town: "missing",
      department: "missing",
    });
  });
});

describe("newPlot", () => {
  it("sends the middle of the farm and its area", () => {
    expect(newPlot(square, " La Esperanza ", "La Plata", "Huila")).toEqual({
      name: "La Esperanza",
      municipality: "La Plata",
      department: "Huila",
      latitude: 2.390_904,
      longitude: -75.889_102,
      area_ha: 4.02,
    });
  });

  it("cuts names to the 80 characters the backend takes", () => {
    expect(newPlot(square, "x".repeat(90), "La Plata", "Huila").name).toHaveLength(80);
  });
});
