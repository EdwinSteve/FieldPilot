import { useCallback, useState } from "react";
import { useResource } from "../../hooks/useResource";
import { lifecycle, type Lot } from "../api/lifecycle";
import { market, type Listing } from "../api/market";

export interface Sales {
  /** Harvests not on sale yet, newest first. */
  ready: Lot[];
  /** The farmer's listings, newest first. Withdrawn ones are not shown. */
  listings: Listing[];
  loading: boolean;
  failed: boolean;
  reload: () => void;
}

async function loadSales(plotId: number) {
  const [lots, listings] = await Promise.all([lifecycle.lots(plotId), market.listings()]);
  return { lots, listings };
}

/** The plot's harvests and the farmer's listings, read together (GET /plots/{id}/lots, GET /listings). */
export function useSales(plotId: number): Sales {
  const [version, setVersion] = useState(0);
  const resource = useResource(
    useCallback(() => loadSales(plotId), [plotId]),
    version,
  );
  const lots = resource.data?.lots ?? [];
  const listings = resource.data?.listings ?? [];
  // A lot with a live listing is on sale; a withdrawn one can be sold again.
  const onSale = new Set(listings.filter((listing) => listing.status !== "withdrawn").map((l) => l.lot_code));
  return {
    ready: lots.filter((lot) => !onSale.has(lot.code)).toSorted((a, b) => b.harvested_on.localeCompare(a.harvested_on)),
    listings: listings.filter((listing) => listing.status !== "withdrawn").toSorted((a, b) => b.id - a.id),
    loading: resource.loading && resource.data === null,
    failed: resource.error !== null && resource.data === null,
    reload: () => setVersion((v) => v + 1),
  };
}
