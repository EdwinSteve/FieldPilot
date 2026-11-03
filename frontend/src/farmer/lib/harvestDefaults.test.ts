import { describe, expect, it } from "vitest";
import {
  bagChoiceOf,
  DEFAULT_HARVEST,
  fromStoredHarvest,
  toStoredHarvest,
  openingUnit,
  typedBagKg,
} from "./harvestDefaults";

describe("the harvest defaults saved on this phone", () => {
  it("round-trips the unit and the bag size", () => {
    const defaults = { unit: "kg", bagKg: 62.5 } as const;
    expect(fromStoredHarvest(toStoredHarvest(defaults))).toEqual(defaults);
  });

  it("keeps Ask each time", () => {
    expect(fromStoredHarvest(toStoredHarvest({ unit: "ask", bagKg: 25 }))).toEqual({ unit: "ask", bagKg: 25 });
  });

  it("starts from bags of 50 kg", () => {
    expect(fromStoredHarvest(null)).toEqual({ unit: "bags", bagKg: 50 });
  });

  it("ignores what it cannot trust, one part at a time", () => {
    expect(fromStoredHarvest("not json")).toEqual(DEFAULT_HARVEST);
    expect(fromStoredHarvest('{"version":2,"unit":"kg","bagKg":40}')).toEqual(DEFAULT_HARVEST);
    expect(fromStoredHarvest('{"version":1,"unit":"sacks","bagKg":40}')).toEqual({ unit: "bags", bagKg: 40 });
    expect(fromStoredHarvest('{"version":1,"unit":"kg","bagKg":-3}')).toEqual({ unit: "kg", bagKg: 50 });
    expect(fromStoredHarvest('{"version":1,"unit":"kg","bagKg":"40"}')).toEqual({ unit: "kg", bagKg: 50 });
  });
});

describe("the bag size as the choices show it", () => {
  it("picks a preset when it is one", () => {
    expect(bagChoiceOf(25)).toEqual({ choice: 25, other: "" });
    expect(bagChoiceOf(50)).toEqual({ choice: 50, other: "" });
  });

  it("fills in Other with a comma, as Colombia writes decimals", () => {
    expect(bagChoiceOf(62.5)).toEqual({ choice: "other", other: "62,5" });
    expect(bagChoiceOf(40)).toEqual({ choice: "other", other: "40" });
  });
});

describe("the unit the harvest form opens on", () => {
  it("is none when the farmer asked to be asked", () => {
    expect(openingUnit("ask")).toBeNull();
    expect(openingUnit("kg")).toBe("kg");
    expect(openingUnit("bags")).toBe("bags");
  });
});

describe("a bag size typed in Other", () => {
  it("is a size only when it is above zero", () => {
    expect(typedBagKg("62,5")).toBe(62.5);
    expect(typedBagKg("40")).toBe(40);
    expect(typedBagKg("0")).toBeNull();
    expect(typedBagKg("")).toBeNull();
  });
});
