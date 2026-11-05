import { describe, expect, it } from "vitest";
import { demo } from "../fixtures/snapshots";
import { fromCache, toCache } from "./farmCache";

describe("the farm cache", () => {
  it("round-trips a read with the time it was saved", () => {
    expect(fromCache(toCache(demo.day2Cycle, 1_700_000_000_000))).toEqual({
      snapshot: demo.day2Cycle,
      savedAt: 1_700_000_000_000,
    });
  });

  it("is empty with nothing stored", () => {
    expect(fromCache(null)).toBeNull();
  });

  it("ignores what it cannot trust", () => {
    expect(fromCache("not json")).toBeNull();
    expect(fromCache('{"version":1,"snapshot":{}}')).toBeNull();
    expect(fromCache('{"version":2,"snapshot":{}}')).toBeNull();
    // Version 3 has no crop stage order (D077).
    expect(fromCache('{"version":3,"snapshot":{},"savedAt":1}')).toBeNull();
    expect(fromCache('{"version":4}')).toBeNull();
    expect(fromCache('{"version":4,"snapshot":{}}')).toBeNull();
  });
});
