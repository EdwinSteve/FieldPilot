// What a signed-in phone keeps between visits (D082, docs/api.md §2.3). Pure logic only.
//
// Only the refresh token is stored: the access token lives in memory and is
// renewed from it after a reload. Signing out deletes both.
import type { Farmer } from "./account";
import type { Home } from "./places";

export interface StoredSession {
  refreshToken: string;
  farmer: Farmer;
}

/** Who last used this phone: Start opens the log-in, and the map their town. Never shown to the next person. */
export interface KnownFarmer {
  name: string;
  phone: string;
  /** Chosen at sign-up; the backend keeps no home town, so this phone does. */
  home: Home | null;
}

const VERSION = 1;
/** The farmer known on this phone: version 2 keeps a chosen town, not a typed city. */
const KNOWN_VERSION = 2;

function parse(text: string | null): Record<string, unknown> | null {
  if (text === null) return null;
  try {
    const value: unknown = JSON.parse(text);
    return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

function isFarmer(value: unknown): value is Farmer {
  const farmer = value as Partial<Farmer> | null;
  return (
    typeof farmer?.id === "number" &&
    typeof farmer.name === "string" &&
    typeof farmer.phone === "string"
  );
}

export function toStoredSession(session: StoredSession): string {
  return JSON.stringify({ version: VERSION, ...session });
}

export function fromStoredSession(text: string | null): StoredSession | null {
  const value = parse(text);
  if (value?.version !== VERSION || typeof value.refreshToken !== "string") return null;
  return isFarmer(value.farmer) ? { refreshToken: value.refreshToken, farmer: value.farmer } : null;
}

export function toKnownFarmer(known: KnownFarmer): string {
  return JSON.stringify({ version: KNOWN_VERSION, ...known });
}

function isHome(value: unknown): value is Home {
  const home = value as Partial<Home> | null;
  return typeof home?.department === "string" && typeof home.town === "string";
}

export function fromKnownFarmer(text: string | null): KnownFarmer | null {
  const value = parse(text);
  if (value?.version !== KNOWN_VERSION) return null;
  if (typeof value.name !== "string" || typeof value.phone !== "string") return null;
  return { name: value.name, phone: value.phone, home: isHome(value.home) ? value.home : null };
}
