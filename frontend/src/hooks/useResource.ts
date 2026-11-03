import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api/client";

export interface Resource<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

/**
 * Loads `load()` now and again whenever `version` changes (after an action or
 * on the App's refresh loop). Panels never poll on their own (D071): there is
 * a single interval in the app. The last good data stays visible while a
 * reload fails, and the error is shown next to it.
 */
export function useResource<T>(load: () => Promise<T>, version: number): Resource<T> {
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
    // `version` is a deliberate trigger: it changes after every user action
    // and on every loop refresh, so each panel shows the new state at once.
    // oxlint-disable-next-line react/exhaustive-effect-dependencies
  }, [run, version]);

  return state;
}

/** The backend's Spanish message when there is one. */
export function describeError(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Could not connect to the backend.";
}
