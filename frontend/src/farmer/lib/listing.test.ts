import { describe, expect, it } from "vitest";
import {
  cop,
  farmerShare,
  listingProblems,
  lowestPrice,
  offerProblem,
  plusDaysIso,
  bySelling,
  isOverdue,
  saleStep,
  shelfPrice,
  typedWhole,
} from "./listing";

describe("the shelf price and the farmer's share", () => {
  it("matches the backend's own listing: 3,000 asked is 3,450 on the shelf, 87 % kept", () => {
    expect(shelfPrice(3000)).toBe(3450);
    expect(farmerShare(3000)).toBe(87);
  });

  it("matches an offer: 10 % off 3,000 is 3,135 on the shelf, 86.1 % kept", () => {
    expect(shelfPrice(3000, 10)).toBe(3135);
    expect(farmerShare(3000, 10)).toBe(86.1);
  });

  it("refuses the backend's too-cheap example: 1,000 keeps 74.1 %", () => {
    expect(farmerShare(1000)).toBe(74.1);
  });

  it("knows the lowest price that keeps 80 %", () => {
    expect(lowestPrice()).toBe(1500);
    expect(farmerShare(lowestPrice())).toBeGreaterThanOrEqual(80);
    expect(listingProblems({ price: String(lowestPrice() - 1), kg: "1" }, 10).price).toBe("too_low");
    expect(listingProblems({ price: String(lowestPrice()), kg: "1" }, 10).price).toBeNull();
    expect(lowestPrice(20)).toBe(1875);
  });
});

describe("cop", () => {
  it("writes pesos without cents", () => {
    expect(cop(3450)).toBe("COP 3,450");
    expect(cop(8100.4)).toBe("COP 8,100");
  });
});

describe("the listing form", () => {
  it("wants a price that keeps 80 % and whole kilos up to the harvest", () => {
    expect(listingProblems({ price: "3000", kg: "4000" }, 5000)).toEqual({ price: null, kg: null });
    expect(listingProblems({ price: "", kg: "" }, 5000)).toEqual({ price: "missing", kg: "missing" });
    expect(listingProblems({ price: "1000", kg: "5001" }, 5000)).toEqual({ price: "too_low", kg: "too_much" });
    expect(listingProblems({ price: "3000", kg: "5000" }, 5000.5).kg).toBeNull();
  });

  it("takes only digits", () => {
    expect(typedWhole("3.000 cop")).toBe("3000");
  });
});

describe("offerProblem", () => {
  it("wants 1 to 30 % off, and the share still at 80 %", () => {
    expect(offerProblem("", 3000)).toBe("missing");
    expect(offerProblem("31", 3000)).toBe("too_big");
    expect(offerProblem("10", 3000)).toBeNull();
    expect(offerProblem("25", 1600)).toBe("too_low");
  });
});

describe("a listing past its best-before day", () => {
  it("is overdue while still on the shelf, not before its day nor once expired", () => {
    expect(isOverdue({ status: "active", days_left: -5 })).toBe(true);
    expect(isOverdue({ status: "active", days_left: 0 })).toBe(false);
    expect(isOverdue({ status: "active" })).toBe(false);
    expect(isOverdue({ status: "expired", days_left: -5 })).toBe(false);
  });

  it("goes after what is still selling", () => {
    const listings = [
      { id: 3, status: "active" as const, days_left: -5 },
      { id: 2, status: "active" as const, days_left: 9 },
      { id: 1, status: "expired" as const },
      { id: 4, status: "in_transit" as const },
    ];
    expect(listings.toSorted(bySelling).map((listing) => listing.id)).toEqual([4, 2, 3, 1]);
  });
});

describe("saleStep", () => {
  it("puts each status on the step bar, withdrawn and expired off it", () => {
    expect(saleStep("awaiting_delivery")).toBe(0);
    expect(saleStep("in_transit")).toBe(1);
    expect(saleStep("active")).toBe(2);
    expect(saleStep("sold_out")).toBe(3);
    expect(saleStep("withdrawn")).toBe(-1);
    expect(saleStep("expired")).toBe(-1);
  });
});

describe("plusDaysIso", () => {
  it("counts days across a month", () => {
    expect(plusDaysIso("2027-03-30", 2)).toBe("2027-04-01");
  });
});
