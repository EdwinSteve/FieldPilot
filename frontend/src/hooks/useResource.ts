import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api/client";

export interface Resource<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

/**
 * Loads `load()` now, again whenever `version` changes (after an action), and
 * every `intervalMs` if given. The last good data stays visible while a reload
 * fails, and the error is shown next to it.
 */
export function useResource<T>(load: () => Promise<T>, version: number, intervalMs?: number): Resource<T> {
  const [state, setState] = useState<Resource<T>>({ data: null, error: null, loading: true });

  const run = useCallback(() => {
    load()
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((error: unknown) =>
        setState((previous) => ({ ...previous, error: describeError(error), loading: false })),
      );
  }, [load]);

  useEffect(() => {
    run();
    if (intervalMs === undefined) return undefined;
    const timer = window.setInterval(run, intervalMs);
    return () => window.clearInterval(timer);
    // `version` is a deliberate trigger: it changes after every user action, so
    // each panel shows the new state at once instead of at its next poll.
    // oxlint-disable-next-line react/exhaustive-effect-dependencies
  }, [run, version, intervalMs]);

  return state;
}

/** The backend's Spanish message when there is one. */
export function describeError(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "No se pudo conectar con el backend.";
}
