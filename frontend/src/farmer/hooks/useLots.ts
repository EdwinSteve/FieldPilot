import { useCallback } from "react";
import { useResource } from "../../hooks/useResource";
import { lifecycle, type Lot } from "../api/lifecycle";

/** The plot's harvests so far (GET /plots/{id}/lots); none while they load or fail. */
export function useLots(plotId: number): Lot[] {
  const load = useCallback(() => lifecycle.lots(plotId), [plotId]);
  return useResource(load, 0).data ?? [];
}
