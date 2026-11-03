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
  it("names every planner crop and writes an unknown one as words", () => {
    expect(cropLabel("maize")).toBe("Maize");
    expect(cropLabel("common_bean")).toBe("Beans");
    expect(cropLabel("aguacate_hass")).toBe("aguacate hass");
  });
});
