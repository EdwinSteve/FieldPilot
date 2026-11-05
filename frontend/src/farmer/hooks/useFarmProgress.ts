import { useCallback, useEffect, useState } from "react";
import { useResource } from "../../hooks/useResource";
import { lifecycle } from "../api/lifecycle";
import type { Progress } from "../lib/accountGate";
import { farmStage, type FarmStage } from "../lib/farmStage";

/** As often as the farm's own loop (useFarmRefresh), and only while nothing could be read. */
const RETRY_MS = 3_000;

export interface FarmProgress {
  /** "loading" also while a reload after sign-in is on its way. */
  progress: Progress;
  stage: FarmStage | null;
  /** The plots and cycles could not be read, and nothing was read before. */
  failed: boolean;
  /** Real time of the last try, for "Last tried at". */
  triedAt: number;
  reload: () => void;
}

interface Read {
  farmerId: number;
  stage: FarmStage;
}

/** How far the signed-in farmer is: read after sign-in, and again after they save a farm or a sowing. */
export function useFarmProgress(farmerId: number | null): FarmProgress {
  const [version, setVersion] = useState(0);
  const [triedAt, setTriedAt] = useState(() => Date.now());
  const load = useCallback(async (): Promise<Read | null> => {
    if (farmerId === null) return null;
    const [plots, cycles] = await Promise.all([lifecycle.plots(), lifecycle.cycles()]);
    return { farmerId, stage: farmStage(plots, cycles) };
  }, [farmerId]);
  const resource = useResource(load, version);
  // A read for the farmer signed in before is not this farmer's progress.
  const read = resource.data?.farmerId === farmerId ? resource.data : null;
  const failed = read === null && resource.error !== null && !resource.loading;
  const reload = useCallback(() => {
    setTriedAt(Date.now());
    setVersion((current) => current + 1);
  }, []);

  // "I will keep trying on my own", as the farm's error screen says.
  useEffect(() => {
    if (!failed) return undefined;
    const timer = window.setInterval(reload, RETRY_MS);
    return () => window.clearInterval(timer);
  }, [failed, reload]);

  return { progress: read?.stage.stage ?? "loading", stage: read?.stage ?? null, failed, triedAt, reload };
}
