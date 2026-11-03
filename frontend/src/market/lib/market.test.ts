import { describe, expect, it } from "vitest";
import { hrefOf, lotHref, parseRoute, tabOf, type MarketRoute } from "./route";
import { addressProblem, clampKg, daysUntil, isFresh, labelOfName, priceSplit } from "./shop";

describe("the marketplace routes", () => {
  it.each<[MarketRoute]>([
    [{ screen: "shop" }],
    [{ screen: "product", id: 4 }],
    [{ screen: "cart" }],
    [{ screen: "order", id: 12 }],
    [{ screen: "lot", code: "FP-2-20270302-1" }],
    [{ screen: "warehouse" }],
  ])("round-trips %j", (route) => {
    expect(parseRoute(hrefOf(route))).toEqual(route);
  });

  it("opens the shop for anything unknown or malformed", () => {
    expect(parseRoute("")).toEqual({ screen: "shop" });
    expect(parseRoute("#/nope")).toEqual({ screen: "shop" });
    expect(parseRoute("#/product/abc")).toEqual({ screen: "shop" });
    expect(parseRoute("#/lot/<script>")).toEqual({ screen: "shop" });
  });

  it("opens a lot from the backend's passport path", () => {
    expect(lotHref("/trace/FP-3-20261102-1")).toBe("#/lot/FP-3-20261102-1");
  });

  it("files each screen under its tab", () => {
    expect(tabOf({ screen: "product", id: 1 })).toBe("shop");
    expect(tabOf({ screen: "lot", code: "FP-1-20270101-1" })).toBe("shop");
    expect(tabOf({ screen: "order", id: 1 })).toBe("orders");
    expect(tabOf({ screen: "cart" })).toBe("cart");
  });
});

describe("the shop's own arithmetic", () => {
  it("asks for whole kilos, never more than the warehouse holds", () => {
    expect(clampKg(3, 3980)).toBe(3);
    expect(clampKg(5000, 3980.6)).toBe(3980);
    expect(clampKg(-1, 10)).toBe(0);
    expect(clampKg(2.6, 10)).toBe(3);
  });

  it("splits the backend's offer price into its three parts", () => {
    const split = priceSplit({ farmer_cop: 2700, logistics_cop: 300, platform_cop: 135, total_cop: 3135, farmer_share_pct: 86.1, discount_pct: 10 });
    expect(split.farmer).toBeCloseTo(0.861, 3);
    expect(split.farmer + split.logistics + split.platform).toBeCloseTo(1, 6);
  });

  it("counts days and freshness", () => {
    expect(daysUntil("2027-03-07", "2027-03-05")).toBe(2);
    expect(isFresh("2027-03-01", "2027-03-05")).toBe(true);
    expect(isFresh("2027-02-01", "2027-03-05")).toBe(false);
  });

  it("names a cart line as the farmer app names the crop", () => {
    expect(labelOfName("Groundnut")).toBe("Peanuts");
    expect(labelOfName("Common bean")).toBe(labelOfName("common_bean"));
  });

  it("wants an address to deliver to", () => {
    expect(addressProblem("  ")).toBe("missing");
    expect(addressProblem("Calle 80 # 10-20, Bogotá")).toBeNull();
  });
});
