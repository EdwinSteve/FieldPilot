import { useState } from "react";
import { describeError } from "./useResource";

export interface Action {
  busy: boolean;
  error: string | null;
  /** Runs `act`, shows its error if any, then asks every panel to refresh. */
  run: (act: () => Promise<unknown>) => Promise<void>;
}

export function useAction(refresh: () => void): Action {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(act: () => Promise<unknown>): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      await act();
    } catch (caught) {
      setError(describeError(caught));
    } finally {
      setBusy(false);
      refresh();
    }
  }

  return { busy, error, run };
}
