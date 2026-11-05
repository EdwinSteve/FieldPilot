// A short buzz that says "your tap landed", for hands busy with the field.

const TAP_MS = 20;

interface Vibrates {
  vibrate?: (pattern: number) => boolean;
}

/** Does nothing on phones and browsers that cannot vibrate. */
export function buzz(device: Vibrates = navigator): void {
  try {
    device.vibrate?.(TAP_MS);
  } catch {
    // Some browsers throw while the page has not been touched yet: the buzz is a nicety.
  }
}
