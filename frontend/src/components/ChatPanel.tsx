import { useCallback, useRef, useState } from "react";
import { api } from "../api/endpoints";
import { fetchHealth } from "../api/health";
import { describeError, useResource } from "../hooks/useResource";
import { isMockModeChatError } from "../lib/chatMode";
import { type Recording, startRecording } from "../lib/recorder";
import type { ChatAnswer, Plot, VoiceAnswer } from "../types/api";
import { Panel } from "./Panel";

interface Exchange {
  id: number;
  question: string;
  /** Only for voice: what the service understood (D061). */
  heard: boolean;
  answer: string;
}

interface ChatPanelProps {
  plot: Plot;
  version: number;
  refresh: () => void;
}

/** Ask by text or voice. Every answer passed the answer_farmer check (D053). */
export function ChatPanel({ plot, version, refresh }: ChatPanelProps) {
  const [question, setQuestion] = useState("");
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const recorder = useRef<Recording | null>(null);
  const nextId = useRef(1);
  // Up front when the backend says so (D072); latched on the first 503 until then.
  const health = useResource(useCallback(() => fetchHealth(), []), version);
  const [mockMode, setMockMode] = useState(false);
  const unavailable = health.data?.mock_llm === true || mockMode;

  async function ask(send: () => Promise<{ question: string; heard: boolean; reply: ChatAnswer }>) {
    setBusy(true);
    setError(null);
    try {
      const { question: asked, heard, reply } = await send();
      const exchange = { id: nextId.current++, question: asked, heard, answer: describeReply(reply) };
      setExchanges((previous) => [...previous, exchange]);
    } catch (caught) {
      if (isMockModeChatError(caught)) {
        setMockMode(true);
      } else {
        setError(describeError(caught));
      }
    } finally {
      setBusy(false);
      refresh();
    }
  }

  function sendText() {
    const text = question.trim();
    if (!text) return;
    setQuestion("");
    return ask(async () => ({ question: text, heard: false, reply: await api.chat(plot.id, text) }));
  }

  async function toggleRecording() {
    if (!recording) {
      try {
        recorder.current = await startRecording();
        setRecording(true);
        setError(null);
      } catch {
        setError("No se pudo usar el micrófono. Revisa el permiso del navegador.");
      }
      return;
    }
    setRecording(false);
    const wav = await recorder.current?.stop();
    recorder.current = null;
    if (!wav) return;
    await ask(async () => {
      const reply: VoiceAnswer = await api.chatVoice(plot.id, wav);
      return { question: reply.transcript, heard: true, reply };
    });
  }

  return (
    <Panel title="Pregúntale al agente" error={error} icon="mic">
      {exchanges.length === 0 && !busy ? (
        <p className="muted">Haz una pregunta para empezar.</p>
      ) : null}
      <ul className="chat">
        {exchanges.map((exchange) => (
          <li key={exchange.id}>
            <p className="chat__question">
              {exchange.heard ? "Entendí: " : ""}«{exchange.question}»
            </p>
            <p className="chat__answer">{exchange.answer}</p>
          </li>
        ))}
      </ul>
      {unavailable ? (
        <p className="notice">
          El chat está desactivado en el modo de demostración (MOCK_LLM=1). El ciclo diario, las
          aprobaciones y el calendario siguen funcionando. Para preguntar al agente, reinicia con
          MOCK_LLM=0 y una clave de API.
        </p>
      ) : null}
      <form
        className="chat__form"
        onSubmit={(event) => {
          event.preventDefault();
          void sendText();
        }}
      >
        <input
          aria-label="Tu pregunta"
          placeholder="¿Necesita agua el maíz de la zona 2?"
          value={question}
          disabled={busy || recording || unavailable}
          onChange={(event) => setQuestion(event.target.value)}
        />
        <button
          type="submit"
          className="button--primary"
          disabled={busy || recording || unavailable || !question.trim()}
        >
          Preguntar
        </button>
        <button
          type="button"
          className={recording ? "button--recording" : undefined}
          disabled={busy || unavailable}
          onClick={() => void toggleRecording()}
        >
          {recording ? "Detener y enviar" : "Hablar"}
        </button>
      </form>
      {busy ? <p className="chat__thinking">El agente está pensando…</p> : null}
    </Panel>
  );
}

function describeReply(reply: ChatAnswer): string {
  if (reply.answer) return reply.answer;
  return "El agente no terminó su respuesta. Revisa «Lo que hizo el agente».";
}
