// The marketplace's shared state: who is signed in, the route, the cart every screen counts, and the assistant's talk.
import { useSyncExternalStore } from "react";
import { ApiError } from "../api/client";
import { session } from "./api/session";
import { store, type AssistantAnswer, type Cart } from "./api/store";
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

export interface Turn {
  question: string;
  answer: AssistantAnswer | null;
  /** Why there is no answer: the model is off, or the call failed. */
  failed: "unavailable" | "failed" | null;
}

/** The talk with the shopping assistant: kept while the shopper moves between tabs, gone at log-in or log-out. */
export interface Chat {
  turns: readonly Turn[];
  accepted: ReadonlySet<number>;
  busy: boolean;
}

const NO_CHAT: Chat = { turns: [], accepted: new Set(), busy: false };
let chat = NO_CHAT;
/** Bumped when the shopper changes, so an answer to the last shopper never lands in the next one's talk. */
let chatEra = 0;
const chatListeners = new Set<() => void>();

function setChat(change: (current: Chat) => Chat) {
  chat = change(chat);
  chatListeners.forEach((listener) => listener());
}

function subscribeChat(listener: () => void) {
  chatListeners.add(listener);
  return () => chatListeners.delete(listener);
}

export function useChat(): Chat {
  return useSyncExternalStore(subscribeChat, () => chat);
}

/** Ask the assistant; the answer lands in the talk even if the shopper has left the tab. */
export async function askAssistant(question: string): Promise<void> {
  if (chat.busy) return;
  const era = chatEra;
  setChat((current) => ({ ...current, busy: true, turns: [...current.turns, { question, answer: null, failed: null }] }));
  let turn: Turn;
  try {
    turn = { question, answer: await store.ask(question), failed: null };
  } catch (caught) {
    turn = { question, answer: null, failed: caught instanceof ApiError && caught.status === 503 ? "unavailable" : "failed" };
  }
  if (era !== chatEra) return;
  setChat((current) => ({ ...current, busy: false, turns: [...current.turns.slice(0, -1), turn] }));
}

/** Put the assistant's proposed cart into the real one. */
export async function acceptProposal(proposalId: number): Promise<void> {
  const era = chatEra;
  const next = await store.accept(proposalId);
  setCart(next);
  if (era !== chatEra) return;
  setChat((current) => ({ ...current, accepted: new Set(current.accepted).add(proposalId) }));
}

session.subscribe(() => {
  chatEra += 1;
  setChat(() => NO_CHAT);
});

/** A short word on what a tap did, over the bottom bar: what went right, or what went wrong. */
export interface Toast {
  id: number;
  tone: "good" | "needs";
  text: string;
  /** One next step: a link (View cart) or a deed (Undo). */
  action?: { label: string; href: string } | { label: string; run: () => void };
}

/** Long enough to read slowly; a failure stays longer. */
const TOAST_MS = { good: 6000, needs: 9000 } as const;
let toast: Toast | null = null;
let toastCount = 0;
let toastTimer: ReturnType<typeof setTimeout> | undefined;
const toastListeners = new Set<() => void>();

function setToast(next: Toast | null) {
  toast = next;
  toastListeners.forEach((listener) => listener());
}

export function showToast(next: Omit<Toast, "id">): void {
  clearTimeout(toastTimer);
  toastCount += 1;
  const id = toastCount;
  setToast({ ...next, id });
  toastTimer = setTimeout(() => {
    if (toast?.id === id) setToast(null);
  }, TOAST_MS[next.tone]);
}

export function dismissToast(): void {
  clearTimeout(toastTimer);
  setToast(null);
}

export function useToast(): Toast | null {
  return useSyncExternalStore(
    (listener) => {
      toastListeners.add(listener);
      return () => toastListeners.delete(listener);
    },
    () => toast,
  );
}

/** The order just paid for, so its page can say thank you once. */
let placed: number | null = null;

export function markPlaced(orderId: number): void {
  placed = orderId;
}

export function wasJustPlaced(orderId: number): boolean {
  return placed === orderId;
}
