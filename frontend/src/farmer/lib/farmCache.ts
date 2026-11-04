// The last good read of the farm, for when the signal drops. Pure logic only.
import type { FarmSnapshot } from "../view-models/snapshot";

/** Raise this whenever `FarmSnapshot` changes: an older save would miss fields. */
// 6: the snapshot holds every zone (D089); an older copy has only one.
const VERSION = 6;

export interface CachedFarm {
  snapshot: FarmSnapshot;
  /** When the read was saved, in real milliseconds: how old the farm on screen is. */
  savedAt: number;
}

export function toCache(snapshot: FarmSnapshot, savedAt: number): string {
  return JSON.stringify({ version: VERSION, snapshot, savedAt });
}

/** Null for anything that is not a read this version of the app wrote. */
export function fromCache(text: string | null): CachedFarm | null {
  if (text === null) return null;
  try {
    const parsed = JSON.parse(text) as {
      version?: unknown;
      snapshot?: FarmSnapshot;
      savedAt?: unknown;
    };
    if (parsed.version !== VERSION || parsed.snapshot === undefined) return null;
    if (typeof parsed.savedAt !== "number") return null;
    return { snapshot: parsed.snapshot, savedAt: parsed.savedAt };
  } catch {
    return null;
  }
}
