// The farmer app's screens as hash routes. Pure logic only.

export type Route =
  | { screen: "welcome" }
  | { screen: "login" }
  | { screen: "signup" }
  | { screen: "setup" }
  | { screen: "advice" }
  | { screen: "today" }
  | { screen: "talk" }
  | { screen: "updates" }
  | { screen: "decide"; taskId: number }
  | { screen: "field" }
  /** `at`: the zone as it was then, as a report opens it; without it, the zone now. */
  | { screen: "zone"; zoneId: number; at?: string }
  | { screen: "report"; reportId: number }
  | { screen: "plan" }
  | { screen: "stop" }
  | { screen: "settings" }
  | { screen: "sales" };

export type Tab = "today" | "talk" | "updates";

const PLAIN: Record<string, Route> = {
  login: { screen: "login" },
  signup: { screen: "signup" },
  setup: { screen: "setup" },
  advice: { screen: "advice" },
  today: { screen: "today" },
  talk: { screen: "talk" },
  updates: { screen: "updates" },
  field: { screen: "field" },
  plan: { screen: "plan" },
  stop: { screen: "stop" },
  settings: { screen: "settings" },
  sales: { screen: "sales" },
};

/** The moment in "?at=…", when it is a real one. */
function atOf(query: string | undefined): string | undefined {
  if (query === undefined) return undefined;
  const at = new URLSearchParams(query).get("at");
  return at !== null && !Number.isNaN(Date.parse(at)) ? at : undefined;
}

/** "#/decide/3" as a route. An empty hash is Welcome; anything unknown is Today. */
export function parseRoute(hash: string): Route {
  const [path = "", query] = hash.replace(/^#\/?/, "").split("?");
  const [name, id, ...rest] = path.split("/").filter(Boolean);
  if (name === undefined) return { screen: "welcome" };
  if (rest.length > 0) return { screen: "today" };
  if (id === undefined) return PLAIN[name] ?? { screen: "today" };
  const parsed = Number(id);
  if (!Number.isInteger(parsed) || parsed <= 0) return { screen: "today" };
  if (name === "decide") return { screen: "decide", taskId: parsed };
  if (name === "zone") {
    const at = atOf(query);
    return at === undefined ? { screen: "zone", zoneId: parsed } : { screen: "zone", zoneId: parsed, at };
  }
  if (name === "report") return { screen: "report", reportId: parsed };
  return { screen: "today" };
}

export function hrefOf(route: Route): string {
  switch (route.screen) {
    case "welcome":
      return "#/";
    case "decide":
      return `#/decide/${route.taskId}`;
    case "zone":
      return route.at === undefined
        ? `#/zone/${route.zoneId}`
        : `#/zone/${route.zoneId}?at=${encodeURIComponent(route.at)}`;
    case "report":
      return `#/report/${route.reportId}`;
    default:
      return `#/${route.screen}`;
  }
}

/** Welcome and the account screens come before the farm: no tab bar, no sign-in needed. */
export function isEntryScreen(route: Route): boolean {
  return route.screen === "welcome" || route.screen === "login" || route.screen === "signup";
}

/** Setting up the farm and choosing what to sow come before the crop is growing. */
export function isSetupScreen(route: Route): boolean {
  return route.screen === "setup" || route.screen === "advice";
}

/** The tab a screen belongs to, as the design marks it. Entry and setup screens have no tab bar. */
export function tabOf(route: Route): Tab | null {
  if (isEntryScreen(route) || isSetupScreen(route)) return null;
  switch (route.screen) {
    case "talk":
      return "talk";
    case "updates":
    case "report":
      return "updates";
    default:
      return "today";
  }
}
