// The revert card of D011. The backend decides; this only words what it sent.
import { formatDuration } from "./format";

export const WINDOW_LABEL = "Window on the simulated clock";
export const PAUSED_TEXT = "Simulated clock paused: the window does not move";
export const CLOSED_TEXT = "Window closed";

export interface RevertInput {
  /** From the backend: the only thing that enables the button. */
  revertOpen: boolean | null;
  /** Simulated seconds left, as the backend computed them. */
  remainingSeconds: number | null;
  clockPaused: boolean;
  speedFactor: number;
}

export interface RevertCard {
  label: string;
  /** Remaining simulated time, or why the window is not counting. */
  status: string;
  /** Decorative real-time estimate, always marked as one; null when it means nothing. */
  estimate: string | null;
  buttonEnabled: boolean;
  /** Shown next to a disabled button, so the reason is visible. */
  disabledReason: string | null;
}

/** null when the task never had a revert window. */
export function revertCard(input: RevertInput): RevertCard | null {
  if (input.revertOpen === null) return null;
  if (!input.revertOpen) {
    return {
      label: WINDOW_LABEL,
      status: CLOSED_TEXT,
      estimate: null,
      buttonEnabled: false,
      disabledReason: CLOSED_TEXT,
    };
  }
  const remaining = input.remainingSeconds ?? 0;
  const simulated = `${formatDuration(remaining)} of simulated clock left`;
  if (input.clockPaused) {
    return {
      label: WINDOW_LABEL,
      status: `${simulated}. ${PAUSED_TEXT}`,
      estimate: null,
      buttonEnabled: true,
      disabledReason: null,
    };
  }
  return {
    label: WINDOW_LABEL,
    status: simulated,
    estimate: realEstimate(remaining, input.speedFactor),
    buttonEnabled: true,
    disabledReason: null,
  };
}

/** "≈ 52 s real at ×360 (estimate)": remaining ÷ speed, labelled as an estimate (D011). */
export function realEstimate(remainingSeconds: number, speedFactor: number): string | null {
  if (!(speedFactor > 0)) return null;
  const real = Math.round(remainingSeconds / speedFactor);
  return `≈ ${formatDuration(real)} real at ×${speedFactor} (estimate)`;
}
