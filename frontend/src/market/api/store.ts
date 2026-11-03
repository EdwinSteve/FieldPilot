// The routes the marketplace uses (D085, docs/api.md §7–9). One function per route, no logic.
import { ApiError, apiUrl, getJson, postJson } from "../../api/client";
import { session } from "./session";

export interface Price {
  farmer_cop: number;
  logistics_cop: number;
  platform_cop: number;
  total_cop: number;
  farmer_share_pct: number;
  discount_pct: number;
}

export interface Product {
  id: number;
  crop: string;
  crop_name: string;
  unit: "kg";
  price: Price;
  offer: { discount_pct: number; ends_on: string } | null;
  available_kg: number;
  harvested_on: string;
  best_before: string;
  producer: string;
  warehouse: string;
  lot_code: string;
  passport_path: string;
}

export type CartProblem = "out_of_stock" | "not_available";

export interface CartLine {
  listing_id: number;
  crop_name: string;
  quantity_kg: number;
  unit_price_cop: number;
  line_total_cop: number;
  available_kg: number;
  problem: CartProblem | null;
}

export interface Cart {
  lines: CartLine[];
  total_cop: number;
  can_checkout: boolean;
}

export interface OrderLine {
  listing_id: number;
  lot_code: string;
  crop: string;
  crop_name: string;
  quantity_kg: number;
  unit_price_cop: number;
  line_total_cop: number;
  passport_path: string;
}

export type OrderStatus = "paid" | "delivered" | "cancelled";

export interface Order {
  id: number;
  status: OrderStatus;
  total_cop: number;
  payment_ref: string;
  delivery_address: string | null;
  placed_at: string;
  delivered_at: string | null;
  cancelled_at: string | null;
  lines: OrderLine[];
}

export interface Profile {
  delivery_address: string | null;
  consent_profiling: boolean;
  consent_profiling_at: string | null;
}

export type Reason = "REPURCHASE_DUE" | "BOUGHT_TOGETHER" | "FRESH_HARVEST" | "ON_OFFER" | "POPULAR";

export interface Recommendation {
  product: Product;
  score: number;
  reasons: Reason[];
  suggested_kg?: number;
}

export interface Proposal {
  id: number;
  items: { listing_id: number; quantity_kg: number }[];
  note: string;
  status: string;
}

export interface AssistantAnswer {
  answer: string;
  proposal: Proposal | null;
  run_id: string;
}

export type JourneyStep = "commissioning" | "shipping" | "receiving" | "retail_selling";

export interface Passport {
  lot_code: string;
  crop: string;
  crop_name: string;
  producer: string;
  municipality: string;
  department: string;
  area_ha: number;
  sowing_date: string;
  harvested_on: string;
  quantity_kg: number;
  grade: "extra" | "first" | "second";
  cultivation: {
    automated: boolean;
    data_source: "measured" | "declared";
    irrigation_mm_total: number | null;
    irrigation_events: number | null;
    inputs_applied: { type: "fertilizer" | "agrochemical"; date: string }[];
  };
  plan: {
    known: boolean;
    followed_recommendation: boolean;
    own_risk: boolean;
    rank: number | null;
    predicted_p_success: number | null;
  };
  integrity: { verified: boolean; trace_events: number };
  journey: { step: JourneyStep; on: string; quantity_kg: number; place: string | null }[];
}

/** A listing as the warehouse sees it (§8): only what receiving needs. */
export interface IncomingListing {
  id: number;
  lot_code: string;
  crop: string;
  crop_name: string;
  status: string;
  quantity_kg: number;
  warehouse: { name: string };
  shipment: { id: number; status: string; dispatched_kg: number; received_kg: number | null } | null;
}

/** PUT with the same login renewal and error shape as the shared client, which has no PUT. */
async function putJson<T>(path: string, body: unknown): Promise<T> {
  const send = () =>
    fetch(apiUrl(path), {
      method: "PUT",
      body: JSON.stringify(body),
      headers: { "Content-Type": "application/json", ...session.headers() },
    });
  let response = await send();
  if (response.status === 401 && (await session.renew())) response = await send();
  if (!response.ok) {
    const parsed = (await response.json().catch(() => ({}))) as { error?: string; message?: string };
    throw new ApiError(response.status, parsed.error ?? `HTTP ${response.status}`, parsed.message ?? `PUT ${path} failed`);
  }
  return (await response.json()) as T;
}

/** Store and warehouse routes need the user's own login, even in the demo: wait for it first. */
async function signed<T>(call: () => Promise<T>): Promise<T> {
  await session.ensureAccess();
  return call();
}

export const store = {
  products: (q?: string) => getJson<Product[]>(q ? `/store/products?q=${encodeURIComponent(q)}` : "/store/products"),
  product: (id: number) => getJson<Product>(`/store/products/${id}`),
  offersToday: () => getJson<Product[]>("/store/offers/today"),
  profile: () => signed(() => getJson<Profile>("/store/profile")),
  saveProfile: (profile: { delivery_address: string | null; consent_profiling: boolean }) =>
    signed(() => putJson<Profile>("/store/profile", profile)),
  cart: () => signed(() => getJson<Cart>("/store/cart")),
  setItem: (listingId: number, quantityKg: number) =>
    signed(() => putJson<Cart>(`/store/cart/items/${listingId}`, { quantity_kg: quantityKg })),
  checkout: (address: string | null) =>
    signed(() => postJson<Order>("/store/checkout", address === null ? {} : { delivery_address: address })),
  orders: () => signed(() => getJson<Order[]>("/store/orders")),
  order: (id: number) => signed(() => getJson<Order>(`/store/orders/${id}`)),
  cancel: (id: number) => signed(() => postJson<Order>(`/store/orders/${id}/cancel`)),
  recommendations: (k = 6) => signed(() => getJson<Recommendation[]>(`/store/recommendations?k=${k}`)),
  ask: (question: string) => signed(() => postJson<AssistantAnswer>("/store/assistant", { question })),
  accept: (proposalId: number) => signed(() => postJson<Cart>(`/store/cart-proposals/${proposalId}/accept`)),
  passport: (code: string) => getJson<Passport>(`/trace/${encodeURIComponent(code)}`),
  // The warehouse (operator or admin).
  listings: () => signed(() => getJson<IncomingListing[]>("/listings")),
  receive: (shipmentId: number, receivedKg: number, temperatureC: number | null) =>
    signed(() => postJson<unknown>(`/shipments/${shipmentId}/receive`, { received_kg: receivedKg, temperature_c: temperatureC })),
  deliver: (orderId: number) => signed(() => postJson<Order>(`/orders/${orderId}/deliver`)),
};
