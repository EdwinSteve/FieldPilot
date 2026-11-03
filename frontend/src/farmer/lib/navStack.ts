// Where Back leads: the screens the farmer came through. Pure logic only.
import { hrefOf, isEntryScreen, tabOf, type Route } from "./route";

/** Deep enough for any real path through the app; older steps fall off. */
const MAX_DEPTH = 20;

function isTabScreen(route: Route): boolean {
  return route.screen === "today" || route.screen === "talk" || route.screen === "updates";
}

/**
 * The stack after moving to `route`. A tab starts a new path, a return to the
 * screen before is a step back, and anything else is a step forward.
 */
export function nextStack(stack: readonly Route[], route: Route): Route[] {
  if (isEntryScreen(route) || isTabScreen(route)) return [route];
  const href = hrefOf(route);
  const top = stack.at(-1);
  if (top !== undefined && hrefOf(top) === href) return [...stack];
  const before = stack.at(-2);
  if (before !== undefined && hrefOf(before) === href) return stack.slice(0, -1);
  return [...stack, route].slice(-MAX_DEPTH);
}

/** The screen Back opens: the one before, or the tab this screen belongs to. Never an entry screen. */
export function backOf(stack: readonly Route[]): Route {
  const before = stack.at(-2);
  if (before !== undefined && !isEntryScreen(before)) return before;
  const current = stack.at(-1);
  const tab = current === undefined ? null : tabOf(current);
  return { screen: tab ?? "today" };
}
