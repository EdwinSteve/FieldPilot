// Whether the crop's stage can be shown. Pure logic only.
import { stageProgress, type RecordedStage, type StageState } from "../../lib/stages";

/** Past this age a crop has left sowing; the backend saying otherwise is a data gap. */
const SOWING_DAYS = 14;

export interface VisibleStage {
  steps: StageState[];
  current: string;
  next: string | null;
}

/**
 * The stage bar's data, or null when it would mislead: no stage recorded yet, or
 * still "sowing" on a crop too old for it, as when the seed has no temperature history.
 * `order` is the crop's stages from its catalogue entry (D077).
 */
export function visibleStage(
  order: readonly string[],
  recorded: readonly RecordedStage[],
  daysSinceSowing: number,
): VisibleStage | null {
  const progress = stageProgress(order, recorded);
  const index = progress.findIndex((step) => step.state === "current");
  const current = progress[index]?.name;
  if (current === undefined) return null;
  if (current === "sowing" && daysSinceSowing > SOWING_DAYS) return null;
  return {
    steps: progress.map((step) => step.state),
    current,
    next: order[index + 1] ?? null,
  };
}
