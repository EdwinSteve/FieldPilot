import { describe, expect, it } from "vitest";
import { firstPlace, placeAt } from "./place";

describe("firstPlace", () => {
  it("reads the point, municipality and department of the best match", () => {
    const results = [
      { lat: "2.39", lon: "-75.89", address: { town: "La Plata", state: "Huila" } },
      { lat: "0", lon: "0" },
    ];
    expect(firstPlace(results)).toEqual({
      point: { lat: 2.39, lng: -75.89 },
      municipality: "La Plata",
      department: "Huila",
    });
  });

  it("prefers the city to smaller names", () => {
    const results = [{ lat: "2.9", lon: "-75.3", address: { village: "X", city: "Neiva" } }];
    expect(firstPlace(results)?.municipality).toBe("Neiva");
  });

  it("finds nothing in an empty or broken answer", () => {
    expect(firstPlace([])).toBeNull();
    expect(firstPlace({ error: "x" })).toBeNull();
    expect(firstPlace([{ lat: "north" }])).toBeNull();
  });
});

describe("placeAt", () => {
  it("reads a reverse lookup, with blanks for missing names", () => {
    expect(placeAt({ lat: "2.39", lon: "-75.89", address: {} })).toEqual({
      point: { lat: 2.39, lng: -75.89 },
      municipality: "",
      department: "",
    });
  });

  it("has nothing for an answer that is not an object", () => {
    expect(placeAt(null)).toBeNull();
  });
});
