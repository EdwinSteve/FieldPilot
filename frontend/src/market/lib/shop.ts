// What the shop works out for itself: kilos in a cart, the price split, what to say about a product. Pure logic only.
import { cropLabel } from "../../farmer/lib/names";
import type { Price } from "../api/store";

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
export function addressProblem(address: string): "missing" | null {
  return address.trim().length < 6 ? "missing" : null;
}
