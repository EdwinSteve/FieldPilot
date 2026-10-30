// Line-chart scaling for sensor readings. Pure logic only.

export interface Range {
  min: number;
  max: number;
}

/** A padded range around the values; a flat line still gets room to breathe. */
export function seriesRange(values: readonly number[]): Range | null {
  if (values.length === 0) return null;
  let min = values[0] ?? 0;
  let max = values[0] ?? 0;
  for (const value of values) {
    if (value < min) min = value;
    if (value > max) max = value;
  }
  if (min === max) {
    const pad = Math.abs(min) * 0.1 || 1;
    return { min: min - pad, max: max + pad };
  }
  const pad = (max - min) * 0.1;
  return { min: min - pad, max: max + pad };
}

/** Polyline points for values across a width-by-height box, oldest first. */
export function toPoints(
  values: readonly number[],
  width: number,
  height: number,
  range: Range,
): string {
  const span = range.max - range.min || 1;
  return values
    .map((value, i) => {
      const x = values.length < 2 ? width / 2 : (i / (values.length - 1)) * width;
      const y = height - ((value - range.min) / span) * height;
      return `${round1(x)},${round1(y)}`;
    })
    .join(" ");
}

function round1(value: number): number {
  return Math.round(value * 10) / 10;
}
