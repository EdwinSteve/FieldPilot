// When the crop growing should be ready, from its heat so far (D077). Pure logic only.

/** Close enough to say "nearly ready" and to get the bags out. */
export const SOON_DAYS = 14;

export type HarvestTiming =
  | { kind: "ready" }
  | { kind: "soon"; days: number }
  | { kind: "later" }
  /** A manual crop, or too early to tell: no date to promise. */
  | { kind: "unknown" };

export interface CropGrowth {
  /** The stage the backend says the crop is in; null before the first. */
  currentStage: string | null;
  /** The crop's stages in order: the last one is harvest time. */
  stageOrder: readonly string[];
  accumulatedGdd: number;
  /** Null for a crop without a catalogue entry. */
  maturityGdd: number | null;
  daysSinceSowing: number;
}

/**
 * Ready once the crop reaches its last stage or its maturity heat. Otherwise the
 * days left at the pace it has grown so far: rough, so only "about".
 */
export function harvestTiming(growth: CropGrowth): HarvestTiming {
  const last = growth.stageOrder.at(-1);
  if (last !== undefined && growth.currentStage === last) return { kind: "ready" };
  const { maturityGdd, accumulatedGdd, daysSinceSowing } = growth;
  if (maturityGdd === null || maturityGdd <= 0) return { kind: "unknown" };
  if (accumulatedGdd >= maturityGdd) return { kind: "ready" };
  if (accumulatedGdd <= 0 || daysSinceSowing <= 0) return { kind: "unknown" };
  const perDay = accumulatedGdd / daysSinceSowing;
  const days = Math.ceil((maturityGdd - accumulatedGdd) / perDay);
  return days <= SOON_DAYS ? { kind: "soon", days } : { kind: "later" };
}
