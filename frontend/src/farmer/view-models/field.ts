import { api } from "../../api/endpoints";
import type { NormBox } from "../../types/api";
import { en } from "../i18n/en";
import { formatCalendarDate } from "../lib/farmTime";
import { roundReading } from "../lib/soilStatus";
import { zoneName, type FarmSnapshot } from "./snapshot";
import type { FieldView } from "./types";

function isInside(box: NormBox, area: NormBox): boolean {
  const x = (box.x1 + box.x2) / 2;
  const y = (box.y1 + box.y2) / 2;
  return x >= area.x1 && x <= area.x2 && y >= area.y1 && y <= area.y2;
}

export function fieldView(snapshot: FarmSnapshot): FieldView | null {
  const { scene, zones, boxes } = snapshot.imagery;
  const imaging = zones[0];
  if (scene === null || imaging === undefined) return null;
  const zone = zoneName(snapshot);
  const spots = boxes.filter((box) => isInside(box, imaging.area));
  const bare = imaging.bare_soil_pct;
  return {
    caption: en.field.caption(formatCalendarDate(scene.acquired_on), scene.synthetic),
    headline: imaging.low_vigor ? en.field.weak(zone) : en.field.good(zone),
    detail: en.field.spots(spots.length),
    barePct: bare === null ? null : `${Math.round(bare)}%`,
    imageUrl: api.imageryImageUrl(snapshot.plot.id),
    imageAlt: en.field.imageAlt(zone, spots.length),
    zoneLabel: zone,
    zoneArea: imaging.area,
    spots,
  };
}

/** The bare share for a sentence, one decimal at most. */
export function bareSoilPct(snapshot: FarmSnapshot): number | null {
  const bare = snapshot.imagery.zones[0]?.bare_soil_pct ?? null;
  return bare === null ? null : Math.round(roundReading(bare));
}
