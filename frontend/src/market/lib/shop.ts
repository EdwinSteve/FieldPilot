// What the shop works out for itself: kilos in a cart, the price split, what to say about a product. Pure logic only.
import { cropLabel } from "../../farmer/lib/names";
import type { Price, Product } from "../api/store";

/** The most a cart line asks for: what the warehouse holds, in whole kilos. */
export function clampKg(kg: number, availableKg: number): number {
  return Math.max(0, Math.min(Math.floor(availableKg), Math.round(kg)));
}

/** What the shopper typed in the kilos box: null while it is empty, else whole kilos, at most `maxKg`. */
export function kgFromText(text: string, maxKg: number): number | null {
  const digits = text.replace(/\D/g, "");
  return digits === "" ? null : clampKg(Number(digits), maxKg);
}

/** Kilos to buy must be typed and at least 1 before the shopper can go on. */
export function kgProblem(kg: number | null): "missing" | null {
  return kg === null || kg < 1 ? "missing" : null;
}

/** The words for a failure from the backend's error name (`code`), or the table's `other`. */
export function failureWords(table: Record<string, string>, code: string | null): string {
  return (code === null ? undefined : table[code]) ?? table.other ?? "";
}

/** The shelf price split three ways, as fractions of the total: the farmer, transport, FieldPilot. */
export function priceSplit(price: Price): { farmer: number; logistics: number; platform: number } {
  const total = price.total_cop;
  if (!(total > 0)) return { farmer: 0, logistics: 0, platform: 0 };
  return {
    farmer: price.farmer_cop / total,
    logistics: price.logistics_cop / total,
    platform: price.platform_cop / total,
  };
}

/** Days from `today` to `isoDay`, both "YYYY-MM-DD"; negative when past. */
export function daysUntil(isoDay: string, today: string): number {
  return Math.round((Date.parse(`${isoDay}T00:00:00Z`) - Date.parse(`${today}T00:00:00Z`)) / 86_400_000);
}

/** "Just harvested" for a week, as the recommender counts it (config/market.yaml fresh_days). */
export function isFresh(harvestedOn: string, today: string): boolean {
  const age = -daysUntil(harvestedOn, today);
  return age >= 0 && age <= 7;
}

/** The phone's today as "YYYY-MM-DD", for dates the shop shows. */
export function isoToday(nowMs: number): string {
  const now = new Date(nowMs);
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

/** The farmer app's name for a crop the cart names only in English ("Groundnut" is "Peanuts" there too). */
export function labelOfName(cropName: string): string {
  return cropLabel(cropName.trim().toLowerCase().replaceAll(" ", "_"));
}

/** A delivery address worth sending: something to find the door by. */
/** A clearance markdown (the best-before day is near), not the farmer's own offer (D086). */
export function isClearance(product: Pick<Product, "offer">): boolean {
  return product.offer?.source === "clearance";
}

/**
 * How much of its shelf life a product has left, 0 to 1, from the days the backend counts
 * (`days_left`, D086) and the days between harvest and best-before.
 */
export function shelfLeft(harvestedOn: string, bestBefore: string, daysLeft: number): number {
  const life = daysUntil(bestBefore, harvestedOn);
  if (!(life > 0)) return 0;
  return Math.min(1, Math.max(0, daysLeft / life));
}

/** "Bogotá D.C." from "FieldPilot Bogotá D.C. warehouse": the place a shopper knows. */
export function warehouseCity(name: string): string {
  return name.replace(/^FieldPilot\s+/i, "").replace(/\s+warehouse$/i, "");
}

/**
 * The model sometimes copies a recommendation reason code into its answer ("DEAL_FOR_YOU Tomato").
 * Each known code becomes its words; the backend is the real fix, this is the safety net.
 */
export function withoutReasonCodes(text: string, labels: Readonly<Record<string, string>>): string {
  return text.replace(/\b([A-Z]+(?:_[A-Z]+)+)\b(\s+first)?(:?)\s*/g, (whole, code: string, first?: string, colon?: string) => {
    const label = labels[code];
    if (label === undefined) return whole;
    // "DEAL_FOR_YOU first:" is the prompt's ordering showing through: it says nothing to a shopper.
    if (first !== undefined) return "";
    return colon === ":" ? `${label}: ` : `${label} · `;
  });
}

/** What an expired listing threw away: what the warehouse received, less what was sold (D086). */
export function writtenOffKg(listing: {
  quantity_kg: number;
  sold_kg?: number;
  shipment: { received_kg: number | null } | null;
}): number {
  const received = listing.shipment?.received_kg ?? listing.quantity_kg;
  return Math.max(0, received - (listing.sold_kg ?? 0));
}

export function addressProblem(address: string): "missing" | null {
  return address.trim().length < 6 ? "missing" : null;
}
