import { describe, expect, it } from "vitest";
import { EMPTY_DRAFT, fromStoredDraft, toStoredDraft } from "./setupDraft";

describe("the setup draft", () => {
  it("round-trips the answers", () => {
    const draft = {
      crops: ["maize", "common_bean"],
      goals: ["save_water" as const, "less_risk" as const],
      outline: [{ lat: 2.39, lng: -75.89 }],
      farmName: "La Esperanza",
    };
    expect(fromStoredDraft(toStoredDraft(draft))).toEqual(draft);
  });

  it("starts empty with nothing stored or a broken value", () => {
    expect(fromStoredDraft(null)).toEqual(EMPTY_DRAFT);
    expect(fromStoredDraft("{")).toEqual(EMPTY_DRAFT);
    expect(fromStoredDraft('{"version":9}')).toEqual(EMPTY_DRAFT);
  });

  it("drops values it does not know", () => {
    const text = '{"version":1,"crops":[1,"maize"],"goals":["fly"],"outline":[{"lat":"x"}]}';
    expect(fromStoredDraft(text)).toEqual({ ...EMPTY_DRAFT, crops: ["maize"] });
  });
});
