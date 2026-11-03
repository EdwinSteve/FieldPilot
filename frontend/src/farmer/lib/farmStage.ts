// How far the signed-in farmer is: no farm yet, a farm not sown, or a crop growing. Pure logic only.
import type { FarmPlot, StartedCycle } from "../api/lifecycle";

export type FarmStage =
  | { stage: "no_plot" }
  | { stage: "no_cycle"; plot: FarmPlot }
  | { stage: "farming"; plot: FarmPlot; cycle: StartedCycle };

/**
 * `plots` are the farmer's own (GET /plots); `cycles` are every cycle of the
 * deployment (GET /cycles is still global, D082). A plot with a crop growing
 * comes first; otherwise the newest plot waits for its sowing.
 */
export function farmStage(plots: readonly FarmPlot[], cycles: readonly StartedCycle[]): FarmStage {
  for (const plot of plots) {
    const cycle = cycles.find((c) => c.plot_id === plot.id && c.status === "active");
    if (cycle !== undefined) return { stage: "farming", plot, cycle };
  }
  const newest = plots.toSorted((a, b) => b.id - a.id)[0];
  return newest === undefined ? { stage: "no_plot" } : { stage: "no_cycle", plot: newest };
}
