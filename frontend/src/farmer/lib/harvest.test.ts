import { describe, expect, it } from "vitest";
import { ApiError } from "../../api/client";
import {
  harvestFailure,
  harvestKg,
  harvestProblems,
  hasProblem,
  kgText,
  parseAmount,
  typedAmount,
  type HarvestForm,
} from "./harvest";

const limits = { sowingDate: "2026-10-01", today: "2027-02-10", areaHa: 2 };
const form: HarvestForm = { date: "2027-02-01", amount: "40", unit: "bags", bagKg: "50", grade: "first" };

describe("the amount", () => {
  it("reads a comma or a dot as the decimal mark", () => {
    expect(parseAmount("1250,5")).toBe(1250.5);
    expect(parseAmount("1250.5")).toBe(1250.5);
    expect(parseAmount("12 kg")).toBeNaN();
  });

  it("lets in digits and one decimal mark, two places at most", () => {
    expect(typedAmount("12a3,456.7")).toBe("123,45");
    expect(typedAmount("2000")).toBe("2000");
  });

  it("turns bags into kilograms", () => {
    expect(harvestKg(form)).toBe(2000);
    expect(harvestKg({ amount: "1800", unit: "kg", bagKg: "" })).toBe(1800);
  });

  it("writes the total with thousands", () => {
    expect(kgText(2000)).toBe("2,000");
  });
});

describe("harvestProblems", () => {
  it("finds nothing in a good form", () => {
    expect(hasProblem(harvestProblems(form, limits))).toBe(false);
  });

  it("wants a day after sowing and not in the future", () => {
    expect(harvestProblems({ ...form, date: "" }, limits).date).toBe("missing");
    expect(harvestProblems({ ...form, date: "2026-10-01" }, limits).date).toBe("before_sowing");
    expect(harvestProblems({ ...form, date: "2027-02-11" }, limits).date).toBe("future");
  });

  it("wants an amount, the bag size for bags, and a quality", () => {
    expect(harvestProblems({ ...form, amount: "0" }, limits).amount).toBe("missing");
    expect(harvestProblems({ ...form, bagKg: "" }, limits).bag).toBe("missing");
    expect(harvestProblems({ ...form, unit: "kg", bagKg: "" }, limits).bag).toBeNull();
    expect(harvestProblems({ ...form, grade: null }, limits).grade).toBe("missing");
  });

  it("wants bags or kilos chosen when the farmer asked to be asked", () => {
    expect(harvestProblems({ ...form, unit: null }, limits).unit).toBe("missing");
    expect(harvestProblems(form, limits).unit).toBeNull();
    expect(harvestKg({ amount: "40", unit: null, bagKg: "50" })).toBeNaN();
  });

  it("refuses more than 100 t per hectare, as the backend does", () => {
    expect(harvestProblems({ ...form, unit: "kg", amount: "200000" }, limits).amount).toBeNull();
    expect(harvestProblems({ ...form, unit: "kg", amount: "200001" }, limits).amount).toBe("too_much");
  });
});

describe("harvestFailure", () => {
  it("names the backend's refusals", () => {
    expect(harvestFailure(new ApiError(409, "OpenTasksError", "x"))).toBe("open_tasks");
    expect(harvestFailure(new ApiError(409, "InvalidTransitionError", "x"))).toBe("already");
    expect(harvestFailure(new ApiError(422, "InvalidHarvestError", "x"))).toBe("invalid");
    expect(harvestFailure(new TypeError("offline"))).toBe("other");
  });
});
