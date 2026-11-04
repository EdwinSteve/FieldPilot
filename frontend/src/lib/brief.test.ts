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

const EMPTY_BRIEF = {
  zones: [],
  sceneId: null,
  imaging: [],
  proposals: [],
  health: [],
  nutrition: [],
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
      health: [],
      nutrition: [],
    });
  });

  it("reads an empty brief as empty", () => {
    expect(parseBrief({})).toEqual(EMPTY_BRIEF);
  });

  it("skips entries with the wrong shape instead of breaking", () => {
    expect(
      parseBrief({
        assessment: { zones: [{ zone_id: "two", status: "dry" }, null, 42] },
        imaging: { zones: "none" },
        proposals: [{ task_id: 1 }],
      }),
    ).toEqual(EMPTY_BRIEF);
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

describe("the agronomist's specialists in the brief (D093)", () => {
  it("reads crop health and soil nutrition per zone", () => {
    const parsed = parseBrief({
      assessment: { zones: [] },
      health: [{ zone_id: 1, risk: "moderate", threats: ["fungal_disease"], note: "", cited: [] }],
      nutrition: [{ zone_id: 1, status: "low", deficits: ["nitrogen", "ph_low"], note: "", cited: [] }],
    });
    expect(parsed.health).toEqual([{ zoneId: 1, level: "moderate", items: ["fungal_disease"] }]);
    expect(parsed.nutrition).toEqual([{ zoneId: 1, level: "low", items: ["nitrogen", "ph_low"] }]);
  });
});
