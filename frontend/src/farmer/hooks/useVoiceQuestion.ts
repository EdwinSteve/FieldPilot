import { useCallback, useRef, useState } from "react";
import { api } from "../../api/endpoints";
import { type Recording, startRecording } from "../../lib/recorder";
import { lookedAtOfRun, type LookedAt } from "../lib/lookedAt";
import { micFailure, sendFailure, type VoiceFailure } from "../lib/voiceFailure";
import type { VoiceExchange, VoiceStatus } from "../view-models/types";

/** A forgotten mic must not stay open: it sends itself after a minute. */
const MAX_RECORDING_MS = 60_000;
const TRACE_EVENTS = 100;

interface OpenRecording {
  recording: Recording;
  startedAt: number;
  timer: number;
}

export interface VoiceQuestion {
  status: VoiceStatus;
  failure: VoiceFailure | null;
  exchanges: VoiceExchange[];
  toggle: () => void;
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

/** Push to talk, read-only: it asks, and it never acts (D057). Kept above the screens. */
export function useVoiceQuestion(plotId: number | undefined): VoiceQuestion {
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [failure, setFailure] = useState<VoiceFailure | null>(null);
  const [exchanges, setExchanges] = useState<VoiceExchange[]>([]);
  const open = useRef<OpenRecording | null>(null);
  // Bumped by `cancel`, so a mic that opens late knows it is no longer wanted.
  const attempt = useRef(0);
  const nextId = useRef(1);

  const send = useCallback(async () => {
    const current = open.current;
    if (current === null || plotId === undefined) return;
    open.current = null;
    window.clearTimeout(current.timer);
    const durationMs = Date.now() - current.startedAt;
    setStatus("thinking");
    try {
      const reply = await api.chatVoice(plotId, await current.recording.stop());
      const lookedAt = await sourcesOf(reply.run_id);
      const exchange: VoiceExchange = {
        id: nextId.current++,
        durationMs,
        question: reply.transcript,
        answer: reply.answer,
        lookedAt,
      };
      setExchanges((previous) => [...previous, exchange]);
    } catch (error) {
      setFailure(sendFailure(error));
    } finally {
      setStatus("idle");
    }
  }, [plotId]);

  const begin = useCallback(async () => {
    const mine = ++attempt.current;
    setFailure(null);
    setStatus("starting");
    try {
      const recording = await startRecording();
      if (mine !== attempt.current) {
        await recording.stop();
        return;
      }
      const timer = window.setTimeout(() => void send(), MAX_RECORDING_MS);
      open.current = { recording, startedAt: Date.now(), timer };
      setStatus("listening");
    } catch (error) {
      if (mine !== attempt.current) return;
      setFailure(micFailure(error));
      setStatus("idle");
    }
  }, [send]);

  const toggle = useCallback(() => {
    void (open.current === null ? begin() : send());
  }, [begin, send]);

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

  return { status, failure, exchanges, toggle, cancel };
}
