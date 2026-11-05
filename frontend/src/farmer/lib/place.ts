// A place found by OpenStreetMap's Nominatim, as the plot needs it. Pure logic only.
import type { LatLng } from "./farmOutline";

export interface Place {
  point: LatLng;
  /** The municipality (city, town or village), for POST /plots. */
  municipality: string;
  /** The department ("Huila"), for POST /plots. */
  department: string;
}

/** The fields of a Nominatim jsonv2 answer that the app reads. */
interface NominatimResult {
  lat?: string;
  lon?: string;
  address?: Record<string, string | undefined>;
}

/** Nominatim names a municipality by its size: the first of these it sends. */
const MUNICIPALITY_KEYS = ["city", "town", "municipality", "village", "county"] as const;

function placeOf(result: NominatimResult | undefined): Place | null {
  const lat = Number(result?.lat);
  const lng = Number(result?.lon);
  if (result === undefined || !Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  const address = result.address ?? {};
  const municipality = MUNICIPALITY_KEYS.map((key) => address[key]).find(Boolean) ?? "";
  return { point: { lat, lng }, municipality, department: address.state ?? "" };
}

/** The best match of a search, or null when nothing was found. */
export function firstPlace(results: unknown): Place | null {
  return Array.isArray(results) ? placeOf(results[0] as NominatimResult | undefined) : null;
}

/** The place under a point, or null when Nominatim has none. */
export function placeAt(result: unknown): Place | null {
  return typeof result === "object" && result !== null ? placeOf(result as NominatimResult) : null;
}
