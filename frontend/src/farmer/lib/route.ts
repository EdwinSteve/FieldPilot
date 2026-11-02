// The farmer app's screens as hash routes. Pure logic only.

export type Route =
  | { screen: "welcome" }
  | { screen: "today" }
  | { screen: "talk" }
  | { screen: "updates" }
  | { screen: "decide"; taskId: number }
  | { screen: "field" }
  | { screen: "zone"; zoneId: number }
  | { screen: "report"; reportId: number }
  | { screen: "plan" }
  | { screen: "stop" };

export type Tab = "today" | "talk" | "updates";

const PLAIN: Record<string, Route> = {
  today: { screen: "today" },
  talk: { screen: "talk" },
  updates: { screen: "updates" },
  field: { screen: "field" },
  plan: { screen: "plan" },
  stop: { screen: "stop" },
};

/** "#/decide/3" as a route. An empty hash is Welcome; anything unknown is Today. */
export function parseRoute(hash: string): Route {
  const [name, id, ...rest] = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  if (name === undefined) return { screen: "welcome" };
  if (rest.length > 0) return { screen: "today" };
  if (id === undefined) return PLAIN[name] ?? { screen: "today" };
  const parsed = Number(id);
  if (!Number.isInteger(parsed) || parsed <= 0) return { screen: "today" };
  if (name === "decide") return { screen: "decide", taskId: parsed };
  if (name === "zone") return { screen: "zone", zoneId: parsed };
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
      return `#/zone/${route.zoneId}`;
    case "report":
      return `#/report/${route.reportId}`;
    default:
      return `#/${route.screen}`;
  }
}

/** The tab a screen belongs to, as the design marks it. Welcome has no tab bar. */
export function tabOf(route: Route): Tab | null {
  switch (route.screen) {
    case "welcome":
      return null;
    case "talk":
      return "talk";
    case "updates":
    case "report":
      return "updates";
    default:
      return "today";
  }
}
