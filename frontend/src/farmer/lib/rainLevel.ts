// How much rain, as a level the farmer reads at a glance. Pure logic only.

export type RainLevel = "none" | "light" | "some" | "heavy";

const DROPS: Record<RainLevel, number> = { none: 0, light: 1, some: 2, heavy: 3 };

/** 0 is none, under 5 mm light, 5 to 20 mm some, above 20 mm heavy. */
export function rainLevel(mm: number): RainLevel {
  if (!(mm > 0)) return "none";
  if (mm < 5) return "light";
  if (mm <= 20) return "some";
  return "heavy";
}

/** How many drops the cloud shows for a level. */
export function rainDrops(level: RainLevel): number {
  return DROPS[level];
}
