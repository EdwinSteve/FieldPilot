import { describe, expect, it } from "vitest";
import { sensorIsStale } from "./sensorHealth";

describe("sensorIsStale", () => {
  const recorded = "2026-11-02T11:00:00Z";

  it("trusts a reading up to two days old", () => {
    expect(sensorIsStale(recorded, "2026-11-04T11:00:00Z")).toBe(false);
  });

  it("flags anything older", () => {
    expect(sensorIsStale(recorded, "2026-11-04T11:00:01Z")).toBe(true);
  });
});
