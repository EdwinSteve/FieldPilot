import { describe, expect, it } from "vitest";
import { neediestZone, type ZoneSoil } from "./zones";

const zone = (id: number, capacity: number, values: number[]): ZoneSoil => ({
  zone: { id, plot_id: 1, name: `Zone ${id}`, area_ha: 0.5, field_capacity_pct: capacity },
  readings: values.map((value, index) => ({ value, recorded_at: `2026-11-0${index + 1}T11:00:00Z` })),
});

describe("neediestZone", () => {
  it("leads with the driest zone for its soil, by the latest reading", () => {
    // Zone 1: 26 of 32 (81%); Zone 2: 18 of 32 (56%).
    expect(neediestZone([zone(1, 32, [20, 26]), zone(2, 32, [25, 18])])?.zone.id).toBe(2);
  });

  it("compares how full, not the bare number", () => {
    // 20 of 40 is half full; 18 of 24 is three quarters.
    expect(neediestZone([zone(1, 24, [18]), zone(2, 40, [20])])?.zone.id).toBe(2);
  });

  it("puts a zone without readings after one with them, and keeps the first between equals", () => {
    expect(neediestZone([zone(1, 32, []), zone(2, 32, [30])])?.zone.id).toBe(2);
    expect(neediestZone([zone(1, 32, [16]), zone(2, 32, [16])])?.zone.id).toBe(1);
    expect(neediestZone([zone(1, 32, []), zone(2, 32, [])])?.zone.id).toBe(1);
  });

  it("is null for a plot with no zones", () => {
    expect(neediestZone([])).toBeNull();
  });
});
