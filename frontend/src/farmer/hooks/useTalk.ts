import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../api/endpoints";
import { type Recording, startRecording } from "../../lib/recorder";
import type { ChatAnswer } from "../../types/api";
import { fromStoredChat, toStoredChat } from "../lib/chatStore";
import { lookedAtOfRun, type LookedAt } from "../lib/lookedAt";
import { micFailure, sendFailure, type TalkFailure } from "../lib/talkFailure";
import type { ChatExchange, TalkStatus } from "../view-models/types";

/** A forgotten mic must not stay open: it sends itself after a minute. */
const MAX_RECORDING_MS = 60_000;
const TRACE_EVENTS = 100;
/** Per tab: a reload keeps the talk, closing the tab forgets it. */
const CHAT_KEY = "fieldpilot.chat";

function readStoredChat(): ChatExchange[] {
  try {
    return fromStoredChat(window.sessionStorage.getItem(CHAT_KEY));
  } catch {
    return [];
  }
}

function storeChat(exchanges: readonly ChatExchange[]): void {
  try {
    window.sessionStorage.setItem(CHAT_KEY, toStoredChat(exchanges));
  } catch {
    // Private mode or a full disk: the talk simply ends with the page.
  }
}

interface OpenRecording {
  recording: Recording;
  startedAt: number;
  timer: number;
}

interface Asked {
  reply: ChatAnswer;
  question: string;
}

export interface Talk {
  status: TalkStatus;
  failure: TalkFailure | null;
  exchanges: ChatExchange[];
  /** The typed question on its way; null while a voice question is unheard. */
  pendingQuestion: string | null;
  draft: string;
  setDraft: (text: string) => void;
  sendDraft: () => void;
  ask: (question: string) => void;
  toggleMic: () => void;
  /** Drops the recording, sending nothing. An answer already on its way still arrives. */
  cancel: () => void;
}

/** "What I looked at" is a nicety: losing it must not lose the answer. */
async function sourcesOf(runId: string): Promise<LookedAt[]> {
  try {
    return lookedAtOfRun(await api.events({ kind: "agent_tool_call", limit: TRACE_EVENTS }), runId);
  } catch {
    return [];
  }
}

/** Asks by text or voice, read-only: it never acts (D057). Kept above the screens. */
export function useTalk(plotId: number | undefined): Talk {
  const [status, setStatus] = useState<TalkStatus>("idle");
  const [failure, setFailure] = useState<TalkFailure | null>(null);
  const [exchanges, setExchanges] = useState<ChatExchange[]>(readStoredChat);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const open = useRef<OpenRecording | null>(null);
  // Bumped by `cancel`, so a mic that opens late knows it is no longer wanted.
  const attempt = useRef(0);
  const nextId = useRef(Math.max(0, ...exchanges.map((exchange) => exchange.id)) + 1);

  useEffect(() => storeChat(exchanges), [exchanges]);

  const ask = useCallback(async (durationMs: number | null, send: () => Promise<Asked>) => {
    setFailure(null);
    setStatus("thinking");
    try {
      const { reply, question } = await send();
      const lookedAt = await sourcesOf(reply.run_id);
      const exchange: ChatExchange = {
        id: nextId.current++,
        durationMs,
        question,
        answer: reply.answer,
        lookedAt,
      };
      setExchanges((previous) => [...previous, exchange]);
      return true;
    } catch (error) {
      setFailure(sendFailure(error));
      return false;
    } finally {
      setPendingQuestion(null);
      setStatus("idle");
    }
  }, []);

  const askTyped = useCallback(
    (text: string) => {
      const question = text.trim();
      if (plotId === undefined || question === "" || status !== "idle") return;
      setDraft("");
      setPendingQuestion(question);
      void ask(null, async () => ({ reply: await api.chat(plotId, question), question })).then(
        (answered) => {
          // A failed question goes back in the box, so it need not be typed again.
          if (!answered) setDraft(question);
        },
      );
    },
    [ask, plotId, status],
  );

  const sendDraft = useCallback(() => askTyped(draft), [askTyped, draft]);

  const sendRecording = useCallback(async () => {
    const current = open.current;
    if (current === null || plotId === undefined) return;
    open.current = null;
    window.clearTimeout(current.timer);
    const durationMs = Date.now() - current.startedAt;
    await ask(durationMs, async () => {
      const reply = await api.chatVoice(plotId, await current.recording.stop());
      return { reply, question: reply.transcript };
    });
  }, [ask, plotId]);

  const startMic = useCallback(async () => {
    const mine = ++attempt.current;
    setFailure(null);
    setStatus("starting");
    try {
      const recording = await startRecording();
      if (mine !== attempt.current) {
        await recording.stop();
        return;
      }
      const timer = window.setTimeout(() => void sendRecording(), MAX_RECORDING_MS);
      open.current = { recording, startedAt: Date.now(), timer };
      setStatus("listening");
    } catch (error) {
      if (mine !== attempt.current) return;
      setFailure(micFailure(error));
      setStatus("idle");
    }
  }, [sendRecording]);

  const toggleMic = useCallback(() => {
    void (open.current === null ? startMic() : sendRecording());
  }, [startMic, sendRecording]);

  const cancel = useCallback(() => {
    attempt.current += 1;
    const current = open.current;
    if (current !== null) {
      open.current = null;
      window.clearTimeout(current.timer);
      void current.recording.stop().catch(() => undefined);
    }
    setStatus((now) => (now === "thinking" ? now : "idle"));
  }, []);

  return {
    status,
    failure,
    exchanges,
    pendingQuestion,
    draft,
    setDraft,
    sendDraft,
    ask: askTyped,
    toggleMic,
    cancel,
  };
}
