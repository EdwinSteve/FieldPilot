// The daily-cycle brief as the stepper shows it. Defensive: unknown shapes read empty.
import type { Json } from "../types/api";

export interface BriefZoneAssessment {
  zoneId: number;
  status: string;
  moisturePct: number | null;
}

export interface BriefZoneImaging {
  zoneId: number;
  ndviMean: number | null;
  bareSoilPct: number | null;
  lowVigor: boolean;
}

export interface BriefProposal {
  taskId: number;
  actionType: string;
  zoneId: number | null;
  outcome: string;
  level: string;
  status: string;
}

export interface ParsedBrief {
  zones: BriefZoneAssessment[];
  sceneId: string | null;
  imaging: BriefZoneImaging[];
  proposals: BriefProposal[];
}

const EMPTY: ParsedBrief = { zones: [], sceneId: null, imaging: [], proposals: [] };

/** Reads the brief JSON of a daily-cycle response; anything odd reads as empty. */
export function parseBrief(brief: Record<string, Json>): ParsedBrief {
  const assessment = asRecord(brief.assessment);
  const imaging = asRecord(brief.imaging);
  const proposals = asArray(brief.proposals);
  if (assessment === null && imaging === null && proposals === null) return EMPTY;
  return {
    zones: (assessment === null ? [] : asArray(assessment.zones) ?? []).flatMap(zoneAssessment),
    sceneId: imaging === null ? null : asString(imaging.scene_id),
    imaging: (imaging === null ? [] : asArray(imaging.zones) ?? []).flatMap(zoneImaging),
    proposals: (proposals ?? []).flatMap(proposal),
  };
}

function zoneAssessment(value: Json): BriefZoneAssessment[] {
  const zone = asRecord(value);
  if (zone === null) return [];
  const zoneId = asNumber(zone.zone_id);
  const status = asString(zone.status);
  if (zoneId === null || status === null) return [];
  return [{ zoneId, status, moisturePct: asNumber(zone.moisture_pct) }];
}

function zoneImaging(value: Json): BriefZoneImaging[] {
  const zone = asRecord(value);
  if (zone === null) return [];
  const zoneId = asNumber(zone.zone_id);
  if (zoneId === null) return [];
  return [
    {
      zoneId,
      ndviMean: asNumber(zone.ndvi_mean),
      bareSoilPct: asNumber(zone.bare_soil_pct),
      lowVigor: asBoolean(zone.low_vigor),
    },
  ];
}

function proposal(value: Json): BriefProposal[] {
  const item = asRecord(value);
  if (item === null) return [];
  const taskId = asNumber(item.task_id);
  const actionType = asString(item.action_type);
  const outcome = asString(item.outcome);
  const level = asString(item.effective_level);
  const status = asString(item.status);
  if (taskId === null || actionType === null || outcome === null || level === null || status === null)
    return [];
  return [{ taskId, actionType, zoneId: asNumber(item.zone_id), outcome, level, status }];
}

type RecordOfJson = { [key: string]: Json };

function asRecord(value: Json | undefined): RecordOfJson | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  return value as RecordOfJson;
}

function asArray(value: Json | undefined): Json[] | null {
  return Array.isArray(value) ? value : null;
}

function asNumber(value: Json | undefined): number | null {
  return typeof value === "number" ? value : null;
}

function asString(value: Json | undefined): string | null {
  return typeof value === "string" ? value : null;
}

function asBoolean(value: Json | undefined): boolean {
  return value === true;
}
