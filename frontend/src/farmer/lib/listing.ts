// Selling a harvest: the price the shop will show, the farmer's share, and what the forms check (D085).
// The fees mirror config/market.yaml; the backend has the final word and refuses with its own error.

export const FEES = {
  /** COP per kg, fixed. */
  logisticsPerKg: 300,
  /** Of the farmer's price, after any offer. */
  platformPct: 5,
  /** A listing or offer under it is refused. */
  minSharePct: 80,
  maxDiscountPct: 30,
  maxOfferDays: 7,
};

/** What a kilo costs on the shelf, for the farmer's price after `discountPct` off. */
export function shelfPrice(farmerPrice: number, discountPct = 0): number {
  const price = farmerPrice * (1 - discountPct / 100);
  return price + FEES.logisticsPerKg + (price * FEES.platformPct) / 100;
}

/** The farmer's share of the shelf price, in %, one decimal. */
export function farmerShare(farmerPrice: number, discountPct = 0): number {
  const price = farmerPrice * (1 - discountPct / 100);
  if (!(price > 0)) return 0;
  return Math.round((price / shelfPrice(farmerPrice, discountPct)) * 1000) / 10;
}

/** The lowest whole price per kg the farmer can ask and still keep the minimum share. */
export function lowestPrice(discountPct = 0): number {
  const keep = FEES.minSharePct / 100;
  const perKg = (keep * FEES.logisticsPerKg) / (1 - keep * (1 + FEES.platformPct / 100));
  // A hair under the next peso is float noise, not a reason to ask one more.
  return Math.ceil(perKg / (1 - discountPct / 100) - 1e-6);
}

/** "COP 3,450": pesos, no cents. */
export function cop(amount: number): string {
  return `COP ${Math.round(amount).toLocaleString("en-US")}`;
}

/** Only digits, as a price or a weight in whole kilos is typed. */
export function typedWhole(text: string): string {
  return text.replace(/\D/g, "").slice(0, 9);
}

export type PriceProblem = "missing" | "too_low";
export type KgProblem = "missing" | "too_much";

export interface ListingProblems {
  price: PriceProblem | null;
  kg: KgProblem | null;
}

export function listingProblems(form: { price: string; kg: string }, harvestedKg: number): ListingProblems {
  const price = Number(form.price);
  const kg = Number(form.kg);
  return {
    // Against the exact lowest price: a share shown as 80.0 % can still be a hair under it.
    price: !(price > 0) ? "missing" : price < lowestPrice() ? "too_low" : null,
    kg: !(kg > 0) ? "missing" : kg > Math.floor(harvestedKg) ? "too_much" : null,
  };
}

export type OfferProblem = "missing" | "too_big" | "too_low";

/** An offer of `discountPct` off the farmer's price: 1 to 30 %, and the share still at the minimum. */
export function offerProblem(discountText: string, farmerPrice: number): OfferProblem | null {
  const discount = Number(discountText);
  if (!(discount >= 1)) return "missing";
  if (discount > FEES.maxDiscountPct) return "too_big";
  return farmerPrice < lowestPrice(discount) ? "too_low" : null;
}

export type ListingStatus = "awaiting_delivery" | "in_transit" | "active" | "sold_out" | "withdrawn" | "expired";

/** The steps a sale goes through, for the step bar. Withdrawn and expired are off the path. */
export const SALE_STEPS = ["listed", "on_the_way", "in_warehouse", "sold_out"] as const;
export type SaleStep = (typeof SALE_STEPS)[number];

const STEP_OF: Record<ListingStatus, number> = {
  awaiting_delivery: 0,
  in_transit: 1,
  active: 2,
  sold_out: 3,
  withdrawn: -1,
  // Past its best-before day: what was left was written off (D086).
  expired: -1,
};

/**
 * On the shelf but past its best-before day: the backend expires it only when told (D086),
 * so the farmer is told now. `daysLeft` below zero means the day has passed.
 */
export function isOverdue(listing: { status: ListingStatus; days_left?: number }): boolean {
  return listing.status === "active" && listing.days_left !== undefined && listing.days_left < 0;
}

/** What is still selling first, newest first; what is past its day or expired after it. */
export function bySelling<T extends { id: number; status: ListingStatus; days_left?: number }>(a: T, b: T): number {
  const over = (listing: T) => (isOverdue(listing) || listing.status === "expired" ? 1 : 0);
  return over(a) - over(b) || b.id - a.id;
}

export function saleStep(status: ListingStatus): number {
  return STEP_OF[status];
}

/** The day `days` after `iso` ("YYYY-MM-DD"), for an offer's last day. */
export function plusDaysIso(iso: string, days: number): string {
  return new Date(Date.parse(`${iso}T00:00:00Z`) + days * 86_400_000).toISOString().slice(0, 10);
}
