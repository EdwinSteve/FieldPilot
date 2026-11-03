import { describe, expect, it } from "vitest";
import { groupRuns } from "./groupRuns";

const day = (item: { day: string }) => item.day;

describe("groupRuns", () => {
  it("groups neighbours with the same key, in order", () => {
    const items = [
      { id: 1, day: "Today" },
      { id: 2, day: "Today" },
      { id: 3, day: "Yesterday" },
    ];
    expect(groupRuns(items, day)).toEqual([
      { key: "Today", items: [items[0], items[1]] },
      { key: "Yesterday", items: [items[2]] },
    ]);
  });

  it("starts a new run when a key comes back later", () => {
    const items = [{ day: "a" }, { day: "b" }, { day: "a" }];
    expect(groupRuns(items, day).map((run) => run.key)).toEqual(["a", "b", "a"]);
  });

  it("has no runs for no items", () => {
    expect(groupRuns([], day)).toEqual([]);
  });
});
