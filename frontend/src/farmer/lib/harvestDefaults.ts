// How the farmer usually counts a harvest, so the harvest form opens with it. Pure logic only.
import { BAG_PRESETS, parseAmount, type Unit } from "./harvest";

/** "ask": the form opens with neither bags nor kilos chosen. */
export type UnitDefault = Unit | "ask";
export const UNIT_DEFAULTS: readonly UnitDefault[] = ["bags", "kg", "ask"];

export interface HarvestDefaults {
  unit: UnitDefault;
  /** Kilos in one of the farmer's bags. */
  bagKg: number;
}

export const DEFAULT_HARVEST: HarvestDefaults = { unit: "bags", bagKg: 50 };

/** A bag size the forms take: one of the presets, or the farmer's own. */
export interface BagChoice {
  choice: number | "other";
  /** What the "Other" field shows; empty for a preset. */
  other: string;
}

const VERSION = 1;

export function toStoredHarvest(defaults: HarvestDefaults): string {
  return JSON.stringify({ version: VERSION, ...defaults });
}

export function fromStoredHarvest(text: string | null): HarvestDefaults {
  let value: Record<string, unknown> | null = null;
  try {
    const parsed: unknown = text === null ? null : JSON.parse(text);
    if (typeof parsed === "object" && parsed !== null) value = parsed as Record<string, unknown>;
  } catch {
    value = null;
  }
  if (value?.version !== VERSION) return DEFAULT_HARVEST;
  const bagKg = value.bagKg;
  return {
    unit: UNIT_DEFAULTS.find((unit) => unit === value.unit) ?? DEFAULT_HARVEST.unit,
    bagKg: typeof bagKg === "number" && bagKg > 0 && Number.isFinite(bagKg) ? bagKg : DEFAULT_HARVEST.bagKg,
  };
}

/** The unit the harvest form opens on: none when the farmer asked to be asked. */
export function openingUnit(unit: UnitDefault): Unit | null {
  return unit === "ask" ? null : unit;
}

/** The saved bag size as the bag choices show it. */
export function bagChoiceOf(bagKg: number): BagChoice {
  if (BAG_PRESETS.includes(bagKg)) return { choice: bagKg, other: "" };
  return { choice: "other", other: String(bagKg).replace(".", ",") };
}

/** The bag size typed in "Other", or null while it is not a size yet. */
export function typedBagKg(text: string): number | null {
  const kg = parseAmount(text);
  return kg > 0 ? kg : null;
}
