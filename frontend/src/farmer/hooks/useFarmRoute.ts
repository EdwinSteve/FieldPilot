import { useSyncExternalStore } from "react";
import { parseRoute, type Route } from "../lib/route";

function subscribe(onChange: () => void): () => void {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}

const readHash = () => window.location.hash;

/** The current screen, from the URL hash. Back and links work as on any web page. */
export function useFarmRoute(): Route {
  return parseRoute(useSyncExternalStore(subscribe, readHash));
}
