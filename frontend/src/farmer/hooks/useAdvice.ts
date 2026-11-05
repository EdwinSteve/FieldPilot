import { useCallback, useEffect, useState } from "react";
import { useResource } from "../../hooks/useResource";
import { lifecycle, type PlantingPlan, type PlotSite } from "../api/lifecycle";

/** docs/api.md §3.2: the site data takes 1 to 3 minutes; poll every 10 s while it builds. */
const SITE_POLL_MS = 10_000;
/** The most the planner serves (MAX_WEEKS): about three months of sowing weeks. */
const PLAN_WEEKS = 12;

export type AdviceState =
  | { status: "loading" }
  | { status: "preparing" }
  | { status: "site_failed"; retrying: boolean; retry: () => void }
  | { status: "plan_failed"; retry: () => void }
  | { status: "ready"; plan: PlantingPlan };

/**
 * The plot's site data, then its planting plan. This poll runs only while the
 * farm is being set up, so it never overlaps the farm's own refresh loop (D071).
 */
export function useAdvice(plotId: number): AdviceState {
  const [siteVersion, setSiteVersion] = useState(0);
  const [planVersion, setPlanVersion] = useState(0);
  const [retrying, setRetrying] = useState(false);
  const site = useResource(
    useCallback(() => lifecycle.site(plotId), [plotId]),
    siteVersion,
  );
  const status = site.data?.status ?? null;
  const ready = status === "ready";
  const plan = useResource(
    useCallback(
      (): Promise<PlantingPlan | null> =>
        ready ? lifecycle.plantingPlan(plotId, PLAN_WEEKS) : Promise.resolve(null),
      [plotId, ready],
    ),
    planVersion,
  );

  useEffect(() => {
    if (status !== "pending" && status !== null) return undefined;
    const timer = window.setInterval(() => setSiteVersion((v) => v + 1), SITE_POLL_MS);
    return () => window.clearInterval(timer);
  }, [status]);

  const rebuild = () => {
    setRetrying(true);
    lifecycle
      .rebuildSite(plotId)
      .catch(() => null)
      .finally(() => {
        setRetrying(false);
        setSiteVersion((v) => v + 1);
      });
  };

  return adviceState(site.data, plan.data, plan.error !== null && !plan.loading, {
    retrying,
    rebuild,
    reloadPlan: () => setPlanVersion((v) => v + 1),
  });
}

function adviceState(
  site: PlotSite | null,
  plan: PlantingPlan | null,
  planFailed: boolean,
  actions: { retrying: boolean; rebuild: () => void; reloadPlan: () => void },
): AdviceState {
  if (site === null) return { status: "loading" };
  if (site.status === "pending") return { status: "preparing" };
  if (site.status !== "ready") {
    return { status: "site_failed", retrying: actions.retrying, retry: actions.rebuild };
  }
  if (plan !== null) return { status: "ready", plan };
  return planFailed ? { status: "plan_failed", retry: actions.reloadPlan } : { status: "loading" };
}
