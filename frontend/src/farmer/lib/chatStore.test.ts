import { describe, expect, it } from "vitest";
import type { ChatExchange } from "../view-models/types";
import { fromStoredChat, toStoredChat } from "./chatStore";

const TYPED: ChatExchange = {
  id: 1,
  durationMs: null,
  question: "Does my maize need water?",
  answer: "Sí, un poco.",
  lookedAt: ["soil"],
};
const SPOKEN: ChatExchange = {
  id: 2,
  durationMs: 4200,
  question: "¿Va a llover?",
  answer: null,
  lookedAt: [],
};

describe("stored chat", () => {
  it("reads back what it saved", () => {
    expect(fromStoredChat(toStoredChat([TYPED, SPOKEN]))).toEqual([TYPED, SPOKEN]);
  });

  it("keeps only the newest 50 questions", () => {
    const many = Array.from({ length: 60 }, (_, index) => ({ ...TYPED, id: index + 1 }));
    const kept = fromStoredChat(toStoredChat(many));
    expect(kept).toHaveLength(50);
    expect(kept[0]?.id).toBe(11);
  });

  it("starts empty with nothing saved, broken text or another shape", () => {
    expect(fromStoredChat(null)).toEqual([]);
    expect(fromStoredChat("{not json")).toEqual([]);
    expect(fromStoredChat(JSON.stringify({ id: 1 }))).toEqual([]);
    expect(fromStoredChat(JSON.stringify([{ ...TYPED, lookedAt: ["moon"] }]))).toEqual([]);
  });
});
