// D092: the store's assistant gets its conversation id back with each follow-up.
import { beforeEach, describe, expect, it, vi } from "vitest";

const ask = vi.fn<(question: string, conversationId?: string) => Promise<unknown>>();
vi.mock("../api/store", () => ({
  store: { ask: (question: string, conversationId?: string) => ask(question, conversationId) },
}));

const { askAssistant } = await import("../state");

describe("the assistant's talk", () => {
  beforeEach(() => ask.mockReset());

  it("starts a conversation, then sends its id with the follow-up", async () => {
    ask.mockResolvedValueOnce({ answer: "Potatoes.", proposal: null, run_id: "r1", conversation_id: "c-1" });
    ask.mockResolvedValueOnce({ answer: "Still potatoes.", proposal: null, run_id: "r2", conversation_id: "c-1" });

    await askAssistant("What should I buy?");
    await askAssistant("What about now?");

    expect(ask.mock.calls).toEqual([["What should I buy?", undefined], ["What about now?", "c-1"]]);
  });
});
