import { describe, expect, it } from "vitest";
import { approvalOutcome } from "./approvalOutcome";

describe("approvalOutcome", () => {
  it.each([
    ["executed", "running"],
    ["scheduled", "planned"],
    ["failed", "not_run"],
    ["pending_approval", "not_run"],
  ] as const)("reads %s as %s", (status, outcome) => {
    expect(approvalOutcome(status)).toBe(outcome);
  });
});
