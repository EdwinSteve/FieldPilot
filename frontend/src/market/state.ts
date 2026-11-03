// The marketplace's shared state: who is signed in, the route, and the cart every screen counts.
import { useSyncExternalStore } from "react";
import { session } from "./api/session";
import { store, type Cart } from "./api/store";
import { parseRoute, type MarketRoute } from "./lib/route";
import type { MarketUser } from "./lib/storedUser";

export function useUser(): MarketUser | null {
  return useSyncExternalStore(session.subscribe, session.current)?.user ?? null;
}

function onHash(listener: () => void) {
  window.addEventListener("hashchange", listener);
  return () => window.removeEventListener("hashchange", listener);
}
const readHash = () => window.location.hash;

export function useRoute(): MarketRoute {
  return parseRoute(useSyncExternalStore(onHash, readHash));
}

let cart: Cart | null = null;
const cartListeners = new Set<() => void>();

function setCart(next: Cart | null) {
  cart = next;
  cartListeners.forEach((listener) => listener());
}

/** Read the cart again; a shopper's only. Any screen that changes the cart hands back the new one. */
export async function refreshCart(): Promise<void> {
  if (session.current()?.user.role !== "customer") {
    setCart(null);
    return;
  }
  try {
    setCart(await store.cart());
  } catch {
    // The cart keeps what it showed; the cart screen says when it fails.
  }
}

export const cartStore = {
  set: setCart,
  subscribe: (listener: () => void) => {
    cartListeners.add(listener);
    return () => cartListeners.delete(listener);
  },
};

export function useCart(): Cart | null {
  return useSyncExternalStore(cartStore.subscribe, () => cart);
}

session.subscribe(() => void refreshCart());
void refreshCart();

/** The order just paid for, so its page can say thank you once. */
let placed: number | null = null;

export function markPlaced(orderId: number): void {
  placed = orderId;
}

export function wasJustPlaced(orderId: number): boolean {
  return placed === orderId;
}
