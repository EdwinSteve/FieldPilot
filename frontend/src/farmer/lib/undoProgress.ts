// How much of an undo window is left. The backend decides; this only measures (D011).

/** The share of the window still open, from 0 to 1. */
export function undoRemaining(
  createdAt: string,
  revertDeadline: string,
  remainingSeconds: number,
): number {
  const windowSeconds = (Date.parse(revertDeadline) - Date.parse(createdAt)) / 1000;
  if (!(windowSeconds > 0)) return 0;
  return Math.min(1, Math.max(0, remainingSeconds / windowSeconds));
}
