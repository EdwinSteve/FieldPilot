// Which screen shows, given who is signed in. Pure logic only.
import { isEntryScreen, type Route } from "./route";

/** Where Start on Welcome leads: the farm, the log-in, or a first account. */
export function startRoute(signedIn: boolean, hasAccount: boolean): Route {
  if (signedIn) return { screen: "today" };
  return { screen: hasAccount ? "login" : "signup" };
}

/**
 * The screen to show for `route`. Signed out, any farm screen shows the log-in
 * in its place, so the farmer lands where they meant to go once signed in.
 */
export function gatedRoute(route: Route, signedIn: boolean, hasAccount: boolean): Route {
  if (signedIn) return route.screen === "login" ? { screen: "today" } : route;
  return isEntryScreen(route) ? route : startRoute(false, hasAccount);
}
