import { useCallback, useEffect, useRef, useState } from "react";

const REFRESH_MS = 3_000;

export interface FarmRefresh {
  version: number;
  /** Real time the newest read was asked for: how old the farm is once it lands. */
  requestedAt: number;
  refresh: () => void;
}

/**
 * The only interval of the farmer app (D071). It re-reads the farm and nothing
 * more: the simulation's ticks stay with the dashboard, so the recorded demo holds.
 */
export function useFarmRefresh(paused = false): FarmRefresh {
  const [tick, setTick] = useState(() => ({ version: 0, requestedAt: Date.now() }));
  /** Set when the timer stops, so starting again reads the farm at once. */
  const wasPaused = useRef(false);
  const refresh = useCallback(() => {
    const requestedAt = Date.now();
    setTick((current) => ({ version: current.version + 1, requestedAt }));
  }, []);

  // Paused while the farmer is on a screen that shows none of the farm (Your sales, Settings):
  // one read on the way back, so Today opens on current numbers.
  useEffect(() => {
    if (paused) return undefined;
    if (wasPaused.current) {
      wasPaused.current = false;
      refresh();
    }
    const timer = window.setInterval(() => {
      if (document.visibilityState !== "hidden") refresh();
    }, REFRESH_MS);
    return () => {
      window.clearInterval(timer);
      wasPaused.current = true;
    };
  }, [paused, refresh]);

  return { ...tick, refresh };
}
