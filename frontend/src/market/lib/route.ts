// The marketplace's screens as hash routes. Pure logic only.

export type MarketRoute =
  | { screen: "shop" }
  | { screen: "product"; id: number }
  | { screen: "cart" }
  | { screen: "orders" }
  | { screen: "order"; id: number }
  | { screen: "assistant" }
  | { screen: "account" }
  | { screen: "lot"; code: string }
  | { screen: "warehouse" };

const PLAIN: Record<string, MarketRoute> = {
  cart: { screen: "cart" },
  orders: { screen: "orders" },
  assistant: { screen: "assistant" },
  account: { screen: "account" },
  warehouse: { screen: "warehouse" },
};

/** A lot code as the backend writes it: FP-<plot>-<date>-<n>. */
const LOT = /^FP-\d+-\d{8}-\d+$/;

/** "#/product/4" as a route. Empty or unknown is the shop. */
export function parseRoute(hash: string): MarketRoute {
  const [name, id, ...rest] = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  if (name === undefined || rest.length > 0) return { screen: "shop" };
  if (id === undefined) return PLAIN[name] ?? { screen: "shop" };
  if (name === "lot") return LOT.test(id) ? { screen: "lot", code: id } : { screen: "shop" };
  const parsed = Number(id);
  if (!Number.isInteger(parsed) || parsed <= 0) return { screen: "shop" };
  if (name === "product") return { screen: "product", id: parsed };
  if (name === "order") return { screen: "order", id: parsed };
  return { screen: "shop" };
}

export function hrefOf(route: MarketRoute): string {
  switch (route.screen) {
    case "shop":
      return "#/";
    case "product":
      return `#/product/${route.id}`;
    case "order":
      return `#/order/${route.id}`;
    case "lot":
      return `#/lot/${route.code}`;
    default:
      return `#/${route.screen}`;
  }
}

/** The lot page for a passport path the backend gives ("/trace/FP-…"). */
export function lotHref(passportPath: string): string {
  return hrefOf({ screen: "lot", code: passportPath.split("/").pop() ?? "" });
}

/** The tab a screen belongs to, for the nav bar. */
export function tabOf(route: MarketRoute): "shop" | "assistant" | "cart" | "orders" | "account" | "warehouse" {
  switch (route.screen) {
    case "product":
    case "lot":
    case "shop":
      return "shop";
    case "order":
      return "orders";
    default:
      return route.screen;
  }
}
