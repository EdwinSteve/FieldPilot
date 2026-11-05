import { describe, expect, it } from "vitest";
import { mobileDisplay, typedFarmName, typedMobile, typedName } from "./typing";

describe("typedName", () => {
  it("keeps letters with accents, spaces, apostrophes, dashes and dots", () => {
    expect(typedName("María-José O'Neil Ma.")).toBe("María-José O'Neil Ma.");
  });

  it("drops numbers and symbols, and doubled spaces", () => {
    expect(typedName("Ana2  Pérez!")).toBe("Ana Pérez");
  });

  it("stops at 120 characters", () => {
    expect(typedName("a".repeat(130))).toHaveLength(120);
  });
});

describe("typedFarmName", () => {
  it("allows numbers too, and stops at 80", () => {
    expect(typedFarmName("Finca La Esperanza, Lote 3")).toBe("Finca La Esperanza, Lote 3");
    expect(typedFarmName("Finca #1 @home")).toBe("Finca 1 home");
    expect(typedFarmName("x".repeat(90))).toHaveLength(80);
  });
});

describe("typedMobile", () => {
  it("keeps digits only, at most 10", () => {
    expect(typedMobile("300 123-45678")).toBe("3001234567");
    expect(typedMobile("abc")).toBe("");
  });

  it("drops a pasted country code", () => {
    expect(typedMobile("+57 300 123 4567")).toBe("3001234567");
    expect(typedMobile("573001234567")).toBe("3001234567");
  });
});

describe("mobileDisplay", () => {
  it("spaces the number as it grows", () => {
    expect(mobileDisplay("300")).toBe("300");
    expect(mobileDisplay("30012")).toBe("300 12");
    expect(mobileDisplay("3001234567")).toBe("300 123 4567");
  });
});
