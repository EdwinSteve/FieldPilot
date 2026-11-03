// Which screen shows, given who is signed in and how far their farm is. Pure logic only.
import { isEntryScreen, isSetupScreen, type Route } from "./route";

/** "loading" until GET /plots and GET /cycles answer. */
export type Progress = "loading" | "no_plot" | "no_cycle" | "farming";

/** Where the farmer belongs for their progress: set up the farm, choose what to sow, or the farm. */
export function homeRoute(progress: Progress): Route {
  if (progress === "no_plot") return { screen: "setup" };
  if (progress === "no_cycle") return { screen: "advice" };
  return { screen: "today" };
}

/** Where Start on Welcome leads: the farm, the log-in, or a first account. */
export function startRoute(signedIn: boolean, knownOnPhone: boolean): Route {
  if (signedIn) return { screen: "today" };
  return { screen: knownOnPhone ? "login" : "signup" };
}

/**
 * The screen to show for `route`. Signed out, any farm screen shows the log-in
 * in its place, so the farmer lands where they meant to go once signed in.
 * Signed in, setting up the farm and choosing what to sow come first; once a
 * crop is growing, those screens are done and open Today.
 */
export function gatedRoute(
  route: Route,
  signedIn: boolean,
  knownOnPhone: boolean,
  progress: Progress,
): Route {
  if (!signedIn) return isEntryScreen(route) ? route : startRoute(false, knownOnPhone);
  if (route.screen === "welcome" || progress === "loading") return route;
  if (progress !== "farming") return homeRoute(progress);
  return isEntryScreen(route) || isSetupScreen(route) ? homeRoute(progress) : route;
}
