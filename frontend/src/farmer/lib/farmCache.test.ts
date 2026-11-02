import { describe, expect, it } from "vitest";
import { demo } from "../fixtures/snapshots";
import { fromCache, toCache } from "./farmCache";

describe("the farm cache", () => {
  it("round-trips a read", () => {
    expect(fromCache(toCache(demo.day2Cycle))).toEqual(demo.day2Cycle);
  });

  it("is empty with nothing stored", () => {
    expect(fromCache(null)).toBeNull();
  });

  it("ignores what it cannot trust", () => {
    expect(fromCache("not json")).toBeNull();
    expect(fromCache('{"version":1,"snapshot":{}}')).toBeNull();
    expect(fromCache('{"version":2}')).toBeNull();
  });
});
