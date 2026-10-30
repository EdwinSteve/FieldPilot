import { describe, expect, it } from "vitest";
import { groupByLevel } from "./policy";

describe("groupByLevel", () => {
  it("groups action types by level, sorted", () => {
    expect(
      groupByLevel({ irrigation: "autonomous", fertilizer: "approval", extra_irrigation: "notify" }),
    ).toEqual({
      autonomous: ["irrigation"],
      notify: ["extra_irrigation"],
      approval: ["fertilizer"],
    });
  });

  it("ignores unknown levels", () => {
    expect(groupByLevel({ irrigation: "self-driving" })).toEqual({
      autonomous: [],
      notify: [],
      approval: [],
    });
  });
});
