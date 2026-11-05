// The farm the farmer outlines on the map: its size, its middle and what is wrong with it. Pure logic only.

export interface LatLng {
  lat: number;
  lng: number;
}

export type OutlineProblem = "too_few" | "outside_colombia" | "too_large";

/** WGS84 equatorial radius, as Leaflet uses. */
const EARTH_RADIUS_M = 6_378_137;
const SQUARE_METRES_PER_HECTARE = 10_000;
const MIN_POINTS = 3;
/** POST /plots accepts up to 1000 ha (docs/api.md §3.1). */
const MAX_HECTARES = 1000;
/** The planner was trained in Colombia; the backend refuses a plot outside these bounds. */
const COLOMBIA = { south: -4.3, north: 13.5, west: -82, east: -66.8 };

const radians = (degrees: number) => (degrees * Math.PI) / 180;

/** The area on the sphere, in hectares: exact enough for a farm, and zero under three points. */
export function areaHectares(points: readonly LatLng[]): number {
  if (points.length < MIN_POINTS) return 0;
  let sum = 0;
  points.forEach((point, index) => {
    const next = points[(index + 1) % points.length] ?? point;
    sum +=
      radians(next.lng - point.lng) *
      (2 + Math.sin(radians(point.lat)) + Math.sin(radians(next.lat)));
  });
  return Math.abs((sum * EARTH_RADIUS_M * EARTH_RADIUS_M) / 2) / SQUARE_METRES_PER_HECTARE;
}

/** The middle of the corners: the point the backend keeps as the plot's place. */
export function middleOf(points: readonly LatLng[]): LatLng | null {
  if (points.length === 0) return null;
  const total = points.reduce((sum, point) => ({ lat: sum.lat + point.lat, lng: sum.lng + point.lng }), {
    lat: 0,
    lng: 0,
  });
  return { lat: total.lat / points.length, lng: total.lng / points.length };
}

export function inColombia(point: LatLng): boolean {
  return (
    point.lat >= COLOMBIA.south &&
    point.lat <= COLOMBIA.north &&
    point.lng >= COLOMBIA.west &&
    point.lng <= COLOMBIA.east
  );
}

export function outlineProblem(points: readonly LatLng[]): OutlineProblem | null {
  if (points.length < MIN_POINTS) return "too_few";
  if (!points.every(inColombia)) return "outside_colombia";
  return areaHectares(points) > MAX_HECTARES ? "too_large" : null;
}

/** "3.5 ha", or "0.25 ha" for a small one: two places under one hectare, one above. */
export function hectaresText(hectares: number): string {
  const places = hectares < 1 ? 2 : 1;
  return `${Number(hectares.toFixed(places))} ha`;
}
