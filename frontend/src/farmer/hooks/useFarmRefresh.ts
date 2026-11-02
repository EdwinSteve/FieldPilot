import { useCallback, useEffect, useState } from "react";

const REFRESH_MS = 3_000;

export interface FarmRefresh {
  version: number;
  refresh: () => void;
}

/**
 * The only interval of the farmer app (D071). It re-reads the farm and nothing
 * more: the simulation's ticks stay with the dashboard, so the recorded demo holds.
 */
export function useFarmRefresh(): FarmRefresh {
  const [version, setVersion] = useState(0);
  const refresh = useCallback(() => setVersion((current) => current + 1), []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState !== "hidden") refresh();
    }, REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [refresh]);

  return { version, refresh };
}
