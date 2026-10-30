import { describe, expect, it } from "vitest";
import { parseBrief } from "./brief";
import type { Json } from "../types/api";

const FULL: Record<string, Json> = {
  plot_id: 1,
  day: "2026-10-28",
  assessment: {
    zones: [{ zone_id: 2, status: "dry", moisture_pct: 21.0, cited: ["reading-1"] }],
    summary: "Zona 2 seca.",
  },
  imaging: {
    scene_id: "neiva-2026-10-28",
    zones: [
      {
        zone_id: 2,
        ndvi_mean: 0.378,
        low_ndvi_pct: 21.2,
        bare_soil_pct: 25.3,
        low_vigor: true,
        cited: ["ndvi-1"],
      },
    ],
  },
  proposals: [
    {
      task_id: 7,
      action_type: "irrigation",
      zone_id: 2,
      outcome: "execute",
      effective_level: "autonomous",
      status: "executed",
    },
  ],
};

describe("parseBrief", () => {
  it("reads zones, imaging and proposals", () => {
    expect(parseBrief(FULL)).toEqual({
      zones: [{ zoneId: 2, status: "dry", moisturePct: 21.0 }],
      sceneId: "neiva-2026-10-28",
      imaging: [{ zoneId: 2, ndviMean: 0.378, bareSoilPct: 25.3, lowVigor: true }],
      proposals: [
        {
          taskId: 7,
          actionType: "irrigation",
          zoneId: 2,
          outcome: "execute",
          level: "autonomous",
          status: "executed",
        },
      ],
    });
  });

  it("reads an empty brief as empty", () => {
    expect(parseBrief({})).toEqual({ zones: [], sceneId: null, imaging: [], proposals: [] });
  });

  it("skips entries with the wrong shape instead of breaking", () => {
    expect(
      parseBrief({
        assessment: { zones: [{ zone_id: "two", status: "dry" }, null, 42] },
        imaging: { zones: "none" },
        proposals: [{ task_id: 1 }],
      }),
    ).toEqual({ zones: [], sceneId: null, imaging: [], proposals: [] });
  });

  it("keeps nulls for unknown measurements", () => {
    const brief = parseBrief({
      assessment: { zones: [{ zone_id: 2, status: "ok", moisture_pct: null }] },
      imaging: {
        scene_id: null,
        zones: [{ zone_id: 2, ndvi_mean: null, bare_soil_pct: null, low_vigor: false }],
      },
    });
    expect(brief.zones).toEqual([{ zoneId: 2, status: "ok", moisturePct: null }]);
    expect(brief.imaging).toEqual([{ zoneId: 2, ndviMean: null, bareSoilPct: null, lowVigor: false }]);
  });
});
