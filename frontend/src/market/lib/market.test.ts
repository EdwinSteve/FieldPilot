import { describe, expect, it } from "vitest";
import { hrefOf, lotHref, parseRoute, tabOf, type MarketRoute } from "./route";
import { addressProblem, clampKg, daysUntil, failureWords, isClearance, isFresh, kgFromText, kgProblem, labelOfName, priceSplit, shelfLeft, warehouseCity, withoutReasonCodes, writtenOffKg } from "./shop";

describe("the assistant's words", () => {
  const labels = { DEAL_FOR_YOU: "A deal on what you like", ON_OFFER: "Offer of the day" };
  it("puts words where the model copied a reason code", () => {
    expect(withoutReasonCodes("DEAL_FOR_YOU Tomato at COP 8700", labels)).toBe("A deal on what you like · Tomato at COP 8700");
    expect(withoutReasonCodes("DEAL_FOR_YOU first: Tomato", labels)).toBe("Tomato");
    expect(withoutReasonCodes("Best for you: DEAL_FOR_YOU first\nTomato", labels)).toBe("Best for you: Tomato");
    expect(withoutReasonCodes("ON_OFFER: beans", labels)).toBe("Offer of the day: beans");
  });

  it("leaves other words, and codes it does not know, as they are", () => {
    expect(withoutReasonCodes("Fresh beans, COP 2400", labels)).toBe("Fresh beans, COP 2400");
    expect(withoutReasonCodes("SOME_CODE here", labels)).toBe("SOME_CODE here");
  });
});

describe("written-off stock", () => {
  it("is what was received, less what was sold", () => {
    expect(writtenOffKg({ quantity_kg: 40, sold_kg: 10, shipment: { received_kg: 38 } })).toBe(28);
    // Nothing weighed on arrival: the listed kilos stand in.
    expect(writtenOffKg({ quantity_kg: 40, shipment: null })).toBe(40);
    expect(writtenOffKg({ quantity_kg: 40, sold_kg: 40, shipment: { received_kg: 40 } })).toBe(0);
  });
});

describe("the product's freshness", () => {
  it("says how much of the shelf life is left", () => {
    // Tomato: 14 days of life, 7 left.
    expect(shelfLeft("2027-03-01", "2027-03-15", 7)).toBe(0.5);
    expect(shelfLeft("2027-03-01", "2027-03-15", 20)).toBe(1);
    expect(shelfLeft("2027-03-01", "2027-03-15", -1)).toBe(0);
    expect(shelfLeft("2027-03-15", "2027-03-15", 0)).toBe(0);
  });

  it("names the warehouse by its city", () => {
    expect(warehouseCity("FieldPilot Bogotá D.C. warehouse")).toBe("Bogotá D.C.");
    expect(warehouseCity("Central")).toBe("Central");
  });
});

describe("clearance", () => {
  it("tells the automatic markdown from the farmer's offer", () => {
    expect(isClearance({ offer: { source: "clearance", discount_pct: 20, ends_on: "2027-03-15" } })).toBe(true);
    expect(isClearance({ offer: { source: "offer", discount_pct: 15, ends_on: "2027-03-07" } })).toBe(false);
    // Before D086 an offer had no source: it was always the farmer's.
    expect(isClearance({ offer: { discount_pct: 15, ends_on: "2027-03-07" } })).toBe(false);
    expect(isClearance({ offer: null })).toBe(false);
  });
});

describe("failure words", () => {
  const table = { OutOfStockError: "Not that much is left.", other: "Try again." };
  it("names the backend's error when it knows it", () => {
    expect(failureWords(table, "OutOfStockError")).toBe("Not that much is left.");
  });
  it("falls back to the general words", () => {
    expect(failureWords(table, "TeapotError")).toBe("Try again.");
    expect(failureWords(table, null)).toBe("Try again.");
    expect(failureWords({}, null)).toBe("");
  });
});

describe("the kilos box", () => {
  it("stays empty while the shopper clears it", () => {
    expect(kgFromText("", 50)).toBeNull();
    expect(kgFromText("kg", 50)).toBeNull();
  });

  it("keeps whole kilos, capped at the stock", () => {
    expect(kgFromText("12", 50)).toBe(12);
    expect(kgFromText("1.5", 50)).toBe(15);
    expect(kgFromText("900", 50.7)).toBe(50);
    expect(kgFromText("0", 50)).toBe(0);
  });

  it("asks for at least one kilo", () => {
    expect(kgProblem(null)).toBe("missing");
    expect(kgProblem(0)).toBe("missing");
    expect(kgProblem(1)).toBeNull();
  });
});

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
