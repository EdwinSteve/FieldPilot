// The last good read of the farm, for when the signal drops. Pure logic only.
import type { FarmSnapshot } from "../view-models/snapshot";

const VERSION = 1;

export function toCache(snapshot: FarmSnapshot): string {
  return JSON.stringify({ version: VERSION, snapshot });
}

/** Null for anything that is not a read this version of the app wrote. */
export function fromCache(text: string | null): FarmSnapshot | null {
  if (text === null) return null;
  try {
    const parsed = JSON.parse(text) as { version?: unknown; snapshot?: FarmSnapshot };
    return parsed.version === VERSION && parsed.snapshot !== undefined ? parsed.snapshot : null;
  } catch {
    return null;
  }
}
