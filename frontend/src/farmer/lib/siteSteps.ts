// What the backend is likely doing while it builds the farm's data (D083 §3.2). Pure logic only.

export type SiteStep = "weather" | "soil" | "climate" | "plan";

/** In the order the build runs; each about a quarter of the usual 2 minutes. */
export const SITE_STEPS: readonly SiteStep[] = ["weather", "soil", "climate", "plan"];
const STEP_MS = 30_000;

/**
 * The step to show as under way, from how long the farmer has waited. The backend
 * does not report its steps, so this paces them; the last one waits until it is done.
 */
export function siteStep(waitedMs: number): number {
  return Math.min(Math.max(Math.floor(waitedMs / STEP_MS), 0), SITE_STEPS.length - 1);
}
