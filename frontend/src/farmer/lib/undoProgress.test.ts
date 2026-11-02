import { describe, expect, it } from "vitest";
import { undoRemaining } from "./undoProgress";

const CREATED = "2026-11-03T11:00:00Z";
const DEADLINE = "2026-11-03T17:00:00Z";

describe("undoRemaining", () => {
  it("is full when the window opens", () => {
    expect(undoRemaining(CREATED, DEADLINE, 21_600)).toBe(1);
  });

  it("measures against the window: 2 h 35 of 6 h is 43%", () => {
    expect(undoRemaining(CREATED, DEADLINE, 9_300)).toBeCloseTo(0.43, 2);
  });

  it("stays between 0 and 1", () => {
    expect(undoRemaining(CREATED, DEADLINE, -5)).toBe(0);
    expect(undoRemaining(CREATED, DEADLINE, 99_999)).toBe(1);
  });

  it("reads an impossible window as closed", () => {
    expect(undoRemaining(DEADLINE, CREATED, 100)).toBe(0);
  });
});
