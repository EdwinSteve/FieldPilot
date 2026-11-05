import { useState, useSyncExternalStore } from "react";
import { backOf, nextStack } from "../lib/navStack";
import { parseRoute, type Route } from "../lib/route";

function subscribe(onChange: () => void): () => void {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}

const readHash = () => window.location.hash;

export interface FarmRoute {
  route: Route;
  /** Where Back leads: the screen the farmer came from. */
  back: Route;
}

interface Path {
  hash: string;
  stack: Route[];
}

/** The current screen, from the URL hash. Back and links work as on any web page. */
export function useFarmRoute(): FarmRoute {
  const hash = useSyncExternalStore(subscribe, readHash);
  const [path, setPath] = useState<Path>(() => ({
    hash,
    stack: nextStack([], parseRoute(hash)),
  }));
  let current = path;
  // A new hash is a step along the path, noted during render so Back is right at once.
  if (path.hash !== hash) {
    current = { hash, stack: nextStack(path.stack, parseRoute(hash)) };
    setPath(current);
  }
  return { route: parseRoute(hash), back: backOf(current.stack) };
}
