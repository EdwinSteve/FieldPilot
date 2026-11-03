// Colombia's departments and towns, for the "Where do you live?" choice. Pure logic only.
import { PLACES } from "../data/places";
import type { LatLng } from "./farmOutline";

/** A town the farmer chose: what POST /plots names, and where the map opens. */
export interface Home {
  department: string;
  town: string;
}

const byName = (a: string, b: string) => a.localeCompare(b, "es");

/** "la plata" and "La Plata", "Bogota" and "Bogotá" are the same place. */
function key(text: string): string {
  return text.normalize("NFD").replace(/\p{Diacritic}/gu, "").trim().toLowerCase();
}

export function departments(): string[] {
  return PLACES.map((place) => place.department).toSorted(byName);
}

export function townsOf(department: string): string[] {
  return (PLACES.find((place) => place.department === department)?.towns ?? [])
    .map(([name]) => name)
    .toSorted(byName);
}

/** The town's centre, for the map to open on. */
export function centreOf(home: Home): LatLng | null {
  const town = PLACES.find((place) => place.department === home.department)?.towns.find(
    ([name]) => name === home.town,
  );
  return town === undefined ? null : { lat: town[1], lng: town[2] };
}

/** The listed place a map lookup names, however it spells it; null when none matches. */
export function matchHome(town: string, department: string): Home | null {
  const place = PLACES.find((candidate) => key(candidate.department) === key(department));
  const found = place?.towns.find(([name]) => key(name) === key(town));
  return place === undefined || found === undefined
    ? null
    : { department: place.department, town: found[0] };
}
