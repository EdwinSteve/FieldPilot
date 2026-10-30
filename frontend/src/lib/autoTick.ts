// When the dashboard may advance the simulation on its own (D070). Pure logic only.
export const AUTO_TICK_MS = 5_000;

/**
 * The dashboard ticks only while the simulated clock runs. A paused clock
 * means paused data (D007, D011), and a hidden tab needs no fresh data.
 */
export function shouldAutoTick(clockPaused: boolean, tabHidden: boolean): boolean {
  return !clockPaused && !tabHidden;
}

/** True once at least AUTO_TICK_MS passed since the last tick attempt. */
export function isTickDue(lastTickMs: number, nowMs: number): boolean {
  return nowMs - lastTickMs >= AUTO_TICK_MS;
}
