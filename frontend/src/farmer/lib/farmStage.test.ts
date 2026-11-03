import { describe, expect, it } from "vitest";
import type { FarmPlot, StartedCycle } from "../api/lifecycle";
import { farmStage } from "./farmStage";

function plot(id: number): FarmPlot {
  return {
    id,
    name: `Plot ${id}`,
    latitude: 2.39,
    longitude: -75.89,
    area_ha: 3.5,
    utc_offset_hours: -5,
    municipality: "La Plata",
    department: "Huila",
  };
}

function cycle(plotId: number, status: string): StartedCycle {
  return {
    id: plotId * 10,
    plot_id: plotId,
    crop: "maize",
    sowing_date: "2026-11-02",
    status,
    accumulated_gdd: 0,
    gdd_updated_through: null,
    stages: [],
    automated: true,
    own_risk: false,
  };
}

describe("farmStage", () => {
  it("has no farm before the first plot", () => {
    expect(farmStage([], [cycle(1, "active")])).toEqual({ stage: "no_plot" });
  });

  it("waits for the sowing on the newest plot", () => {
    expect(farmStage([plot(2), plot(5)], [])).toMatchObject({ stage: "no_cycle", plot: { id: 5 } });
  });

  it("farms the plot with a crop growing, ignoring other farmers' cycles", () => {
    const stage = farmStage([plot(2), plot(5)], [cycle(1, "active"), cycle(2, "active")]);
    expect(stage).toMatchObject({ stage: "farming", plot: { id: 2 }, cycle: { plot_id: 2 } });
  });

  it("treats a harvested plot as waiting for its next sowing", () => {
    expect(farmStage([plot(2)], [cycle(2, "completed")])).toMatchObject({ stage: "no_cycle" });
  });
});
