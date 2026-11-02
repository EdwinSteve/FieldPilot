import { describe, expect, it } from "vitest";
import { cropLabel, farmLabel, zoneLabel } from "./names";

describe("zoneLabel", () => {
  it("translates the word and keeps the number", () => {
    expect(zoneLabel("Zona 2")).toBe("Zone 2");
  });

  it("leaves another name alone", () => {
    expect(zoneLabel("Lote norte")).toBe("Lote norte");
    expect(zoneLabel("Zonal")).toBe("Zonal");
  });
});

describe("farmLabel", () => {
  it("drops the town", () => {
    expect(farmLabel("Finca demo, Neiva")).toBe("Finca demo");
    expect(farmLabel("Finca demo")).toBe("Finca demo");
  });
});

describe("cropLabel", () => {
  it("names a known crop and passes an unknown one through", () => {
    expect(cropLabel("maize")).toBe("Maize");
    expect(cropLabel("sorghum")).toBe("sorghum");
  });
});
