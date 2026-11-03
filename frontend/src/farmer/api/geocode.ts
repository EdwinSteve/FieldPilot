// OpenStreetMap's Nominatim: the town the farmer types, and the place under their farm.
// Free with no key; its usage policy allows a search per user action, never in a loop.
import type { LatLng } from "../lib/farmOutline";
import { firstPlace, placeAt, type Place } from "../lib/place";

const NOMINATIM = "https://nominatim.openstreetmap.org";

async function getJson(url: string): Promise<unknown> {
  const response = await fetch(url, { headers: { "Accept-Language": "es" } });
  if (!response.ok) throw new Error(`Nominatim answered HTTP ${response.status}`);
  return response.json();
}

/** The best match in Colombia for a town or city, or null. */
export async function findPlace(text: string): Promise<Place | null> {
  const query = new URLSearchParams({
    q: text,
    countrycodes: "co",
    format: "jsonv2",
    addressdetails: "1",
    limit: "1",
  });
  return firstPlace(await getJson(`${NOMINATIM}/search?${query.toString()}`));
}

/** The municipality and department under a point, or null. */
export async function placeUnder(point: LatLng): Promise<Place | null> {
  const query = new URLSearchParams({
    lat: String(point.lat),
    lon: String(point.lng),
    format: "jsonv2",
    addressdetails: "1",
    zoom: "10",
  });
  return placeAt(await getJson(`${NOMINATIM}/reverse?${query.toString()}`));
}
