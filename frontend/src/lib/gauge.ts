// Circular gauge geometry: soil moisture against field capacity. Pure logic only.

export interface Point {
  x: number;
  y: number;
}

/** 0° points up, clockwise: the gauge's own convention. */
export function polar(cx: number, cy: number, radius: number, angleDeg: number): Point {
  const angle = ((angleDeg % 360) + 360) % 360;
  const radians = (angle * Math.PI) / 180;
  return { x: cx + radius * Math.sin(radians), y: cy - radius * Math.cos(radians) };
}

/** An SVG arc path from start to end angle (clockwise), with the right large-arc flag. */
export function arcPath(
  cx: number,
  cy: number,
  radius: number,
  startDeg: number,
  endDeg: number,
): string {
  const from = polar(cx, cy, radius, startDeg);
  const to = polar(cx, cy, radius, endDeg);
  const sweep = ((endDeg - startDeg) % 360 + 360) % 360;
  const large = sweep > 180 ? 1 : 0;
  return `M ${round1(from.x)} ${round1(from.y)} A ${radius} ${radius} 0 ${large} 1 ${round1(to.x)} ${round1(to.y)}`;
}

/** How full the soil is: moisture as a fraction of field capacity. Never negative. */
export function gaugeFraction(moisturePct: number | undefined, fieldCapacityPct: number): number {
  if (moisturePct === undefined || !(fieldCapacityPct > 0)) return 0;
  return Math.max(0, moisturePct / fieldCapacityPct);
}

function round1(value: number): number {
  return Math.round(value * 10) / 10;
}
