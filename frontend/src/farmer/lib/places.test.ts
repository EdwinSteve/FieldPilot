import { describe, expect, it } from "vitest";
import { centreOf, departments, matchHome, townsOf } from "./places";

describe("the places of Colombia", () => {
  it("lists the 33 departments in Spanish order", () => {
    const all = departments();
    expect(all).toHaveLength(33);
    expect(all.indexOf("Bolívar")).toBeLessThan(all.indexOf("Boyacá"));
    expect(all).toContain("Huila");
  });

  it("lists a department's towns", () => {
    const huila = townsOf("Huila");
    expect(huila).toHaveLength(37);
    expect(huila).toContain("La Plata");
    expect(townsOf("Nowhere")).toEqual([]);
  });

  it("knows where a town is", () => {
    expect(centreOf({ department: "Huila", town: "La Plata" })).toEqual({
      lat: 2.3893,
      lng: -75.8913,
    });
    expect(centreOf({ department: "Huila", town: "Medellín" })).toBeNull();
  });

  it("matches a map's spelling to the listed place", () => {
    expect(matchHome("la plata", "HUILA")).toEqual({ department: "Huila", town: "La Plata" });
    expect(matchHome("Medellin", "Antioquia")).toEqual({
      department: "Antioquia",
      town: "Medellín",
    });
    expect(matchHome("La Plata", "Antioquia")).toBeNull();
  });
});
