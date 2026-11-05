import { describe, expect, it } from "vitest";
import { fromStoredOutbox, sortOutbox, toStoredOutbox, withAnswer, withoutAnswer } from "./outbox";

const yes = { taskId: 3, answer: "yes", savedAt: 100 } as const;
const no = { taskId: 4, answer: "no", reason: "Wait for the rain", savedAt: 200 } as const;

describe("the saved answers", () => {
  it("round-trip, a reason included", () => {
    expect(fromStoredOutbox(toStoredOutbox([yes, no]))).toEqual([yes, no]);
  });

  it("ignore what they cannot trust", () => {
    expect(fromStoredOutbox(null)).toEqual([]);
    expect(fromStoredOutbox("not json")).toEqual([]);
    expect(fromStoredOutbox('{"version":2,"answers":[]}')).toEqual([]);
    expect(
      fromStoredOutbox('{"version":1,"answers":[{"taskId":3,"answer":"maybe","savedAt":1},{"taskId":5,"answer":"yes","savedAt":2}]}'),
    ).toEqual([{ taskId: 5, answer: "yes", savedAt: 2 }]);
  });

  it("keep one answer per decision, the latest", () => {
    const changed = { taskId: 3, answer: "no", savedAt: 300 } as const;
    expect(withAnswer([yes, no], changed)).toEqual([no, changed]);
    expect(withoutAnswer([yes, no], 3)).toEqual([no]);
  });
});

describe("sortOutbox", () => {
  it("sends what still waits for the farmer and drops the rest", () => {
    expect(sortOutbox([yes, no], new Set([4]))).toEqual({ send: [no], closed: [yes] });
    expect(sortOutbox([], new Set([4]))).toEqual({ send: [], closed: [] });
  });
});
