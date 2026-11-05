// The look of this phone: kept after Sign out, since it belongs to the phone, not the farmer.
import { useSyncExternalStore } from "react";
import { fromStoredLook, themeOf, toStoredLook, type Look } from "../lib/look";

const LOOK_KEY = "fieldpilot.look";
const PHONE_DARK = "(prefers-color-scheme: dark)";
/** The browser bar's colour: the ground of each theme. */
const BAR_COLOURS = { light: "#F3F5F0", dark: "#0F1512" };

function readLook(): Look {
  try {
    return fromStoredLook(window.localStorage.getItem(LOOK_KEY));
  } catch {
    return fromStoredLook(null);
  }
}

function phoneDark(): boolean {
  return window.matchMedia?.(PHONE_DARK).matches ?? false;
}

let look = readLook();
const listeners = new Set<() => void>();

/** farmer.css reads both attributes on <html>, so the whole page changes at once. */
function apply(): void {
  const theme = themeOf(look.theme, phoneDark());
  document.documentElement.dataset.theme = theme;
  document.documentElement.dataset.text = look.text;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", BAR_COLOURS[theme]);
}

// On import, before the first screen paints, so a dark phone never flashes light.
apply();
window.matchMedia?.(PHONE_DARK).addEventListener("change", apply);

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function setLook(next: Look): void {
  look = next;
  try {
    window.localStorage.setItem(LOOK_KEY, toStoredLook(next));
  } catch {
    // Private mode: the look lasts until the page closes.
  }
  // Where the browser can, the old look fades into the new one; elsewhere it changes at once.
  if (typeof document.startViewTransition === "function") document.startViewTransition(apply);
  else apply();
  listeners.forEach((listener) => listener());
}

export function useLook(): [Look, (look: Look) => void] {
  return [useSyncExternalStore(subscribe, () => look), setLook];
}
