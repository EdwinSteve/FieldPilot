// The market routes the farmer uses (D085, docs/api.md §7–8). One function per route, no logic.
import { getJson, postJson } from "../../api/client";
import type { ListingStatus } from "../lib/listing";
import { session } from "./session";

export interface Warehouse {
  id: number;
  code: string;
  name: string;
  municipality: string;
  department: string;
  cold_storage: boolean;
}

export interface Shipment {
  id: number;
  listing_id: number;
  warehouse_id: number;
  status: "dispatched" | "received";
  dispatched_kg: number;
  /** What the warehouse weighed on arrival; null until then. */
  received_kg: number | null;
  temperature_c: number | null;
}

export interface Listing {
  id: number;
  lot_code: string;
  crop: string;
  crop_name: string;
  status: ListingStatus;
  quantity_kg: number;
  farmer_price_per_kg_cop: number;
  shelf_price_per_kg_cop: number;
  farmer_share_pct: number;
  warehouse: Warehouse;
  stock_kg: number;
  sold_kg: number;
  payouts_cop: number;
  shipment: Shipment | null;
  /** The harvest day plus the crop's shelf life (D086). */
  best_before?: string;
  days_left?: number;
  /** The automatic markdown as the best-before day nears; null while there is none. */
  clearance?: { discount_pct: number; ends_on: string } | null;
}

export interface NewListing {
  farmer_price_per_kg_cop: number;
  quantity_kg: number;
  warehouse_id: number;
}

export interface NewOffer {
  discount_pct: number;
  starts_on: string;
  ends_on: string;
}

export type JourneyStep = "commissioning" | "shipping" | "receiving" | "retail_selling";

/** The lot's passport (§7): here only the parts the farmer's own screens show. */
export interface Passport {
  lot_code: string;
  crop_name: string;
  harvested_on: string;
  quantity_kg: number;
  integrity: { verified: boolean; trace_events: number };
  journey: { step: JourneyStep; on: string; quantity_kg: number; place: string | null }[];
}

/** Every market route needs the farmer's own login, even in the demo: wait for it first. */
async function signed<T>(call: () => Promise<T>): Promise<T> {
  await session.ensureAccess();
  return call();
}

export const market = {
  warehouses: () => getJson<Warehouse[]>("/warehouses"),
  listings: () => signed(() => getJson<Listing[]>("/listings")),
  list: (lotCode: string, listing: NewListing) =>
    signed(() => postJson<Listing>(`/lots/${encodeURIComponent(lotCode)}/listings`, listing)),
  dispatch: (listingId: number) => signed(() => postJson<Shipment>(`/listings/${listingId}/dispatch`)),
  withdraw: (listingId: number) => signed(() => postJson<Listing>(`/listings/${listingId}/withdraw`)),
  offer: (listingId: number, offer: NewOffer) =>
    signed(() => postJson<unknown>(`/listings/${listingId}/offers`, offer)),
  passport: (lotCode: string) => getJson<Passport>(`/trace/${encodeURIComponent(lotCode)}`),
};
