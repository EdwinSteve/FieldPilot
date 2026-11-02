import { useEffect, useRef } from "react";
import avatar from "../assets/avatar.png";
import { ChatBar } from "../components/ChatBar";
import { Chip } from "../components/Chip";
import { Icon } from "../components/Icon";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import type { TalkControl, TalkExchange, TalkView } from "../view-models/types";

const WAVE_BARS = ["h-2.5", "h-4.5", "h-3", "h-5", "h-2", "h-3.5"];
const FARMER_BUBBLE = "rounded-[22px_22px_6px_22px] bg-primary px-4.5 py-3.5 text-surface shadow-bubble";

function TypedBubble({ question }: { question: string }) {
  return (
    <p lang="es" className={`max-w-[88%] self-end text-body font-semibold ${FARMER_BUBBLE}`}>
      {question}
    </p>
  );
}

function VoiceBubble({ exchange }: { exchange: TalkExchange }) {
  return (
    <div className="flex max-w-[88%] flex-col items-end gap-1.5 self-end">
      <div className={`flex items-center gap-3 ${FARMER_BUBBLE}`}>
        <Icon name="mic" size={22} />
        <span aria-hidden="true" className="flex items-center gap-0.75">
          {WAVE_BARS.map((height, index) => (
            <span key={index} className={`w-0.75 rounded-sm bg-surface ${height}`} />
          ))}
        </span>
        <span className="text-small font-bold">{exchange.duration}</span>
      </div>
      <span className="text-right text-caption leading-snug text-ink-2">
        {en.talk.understood}{" "}
        <strong lang="es" className="text-ink">
          “{exchange.question}”
        </strong>
      </span>
    </div>
  );
}

function AgentFrame({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-end gap-2">
      <img
        src={avatar}
        alt={en.talk.avatarAlt}
        className="size-10 shrink-0 rounded-full border-2 border-surface object-cover shadow-avatar"
      />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="pl-1.5 text-caption font-extrabold">
          <span className="text-ink">{en.talk.agentFirst}</span>
          <span className="text-primary">{en.talk.agentSecond}</span>
        </span>
        <div className="flex flex-col gap-3 rounded-[22px_22px_22px_6px] border-[1.5px] border-border bg-surface p-4 shadow-bubble-soft">
          {children}
        </div>
      </div>
    </div>
  );
}

function AgentBubble({ exchange }: { exchange: TalkExchange }) {
  return (
    <AgentFrame>
      {exchange.answer === null ? (
        <span className="text-body leading-snug text-ink-2">{en.talk.noAnswer}</span>
      ) : (
        <span lang="es" className="text-lead leading-snug font-bold">
          {exchange.answer}
        </span>
      )}
      {exchange.chips.length > 0 ? (
        <div className="flex flex-col gap-2">
          <span className="text-caption font-bold text-ink-3">{en.talk.lookedAt}</span>
          <div className="flex flex-wrap gap-2">
            {exchange.chips.map((chip) => (
              <Chip key={chip.text} tone={chip.kind === "soil" ? "needs" : "undo"}>
                <Icon name={chip.kind === "soil" ? "drop" : "cloud"} size={16} strokeWidth={2.4} />
                {chip.text}
              </Chip>
            ))}
          </div>
        </div>
      ) : null}
    </AgentFrame>
  );
}

function DecisionsLink({ view }: { view: TalkView }) {
  if (view.decision === null) return null;
  return (
    <a
      href={hrefOf({ screen: "decide", taskId: view.decision.taskId })}
      className="press flex min-h-16 items-center justify-between gap-2.5 rounded-control border-[2.5px] border-needs bg-surface px-4 text-ink no-underline"
    >
      <span className="flex flex-col">
        <span className="text-body font-extrabold">{en.talk.decisionsWaiting(view.waitingCount)}</span>
        <span className="text-caption text-ink-3">{view.decision.question}</span>
      </span>
      <Icon name="forward" size={22} strokeWidth={2.6} className="text-needs" />
    </a>
  );
}

interface TalkScreenProps {
  view: TalkView;
  control: TalkControl;
}

export function TalkScreen({ view, control }: TalkScreenProps) {
  const { cancel, status, pendingQuestion } = control;
  const end = useRef<HTMLDivElement>(null);
  const count = view.exchanges.length;
  const thinking = status === "thinking";

  // Leaving the screen closes the mic: it never listens where it cannot be seen.
  useEffect(() => cancel, [cancel]);

  useEffect(() => {
    if (count > 0 || thinking) end.current?.scrollIntoView({ block: "end" });
  }, [count, thinking]);

  return (
    <>
      <main className="flex min-h-0 flex-1 flex-col gap-3.5 overflow-y-auto px-4.5 pt-7 pb-3">
        <h1 className="mx-0.5 text-title font-extrabold tracking-title">{en.talk.title}</h1>
        <DecisionsLink view={view} />
        <span className="flex items-center gap-2 px-1 text-caption leading-snug text-ink-3">
          <Icon name="info" size={18} className="shrink-0" />
          {en.talk.onlyAnswers}
        </span>
        {view.exchanges.map((exchange) => (
          <div key={exchange.id} className="flex flex-col gap-3.5">
            {exchange.duration === null ? (
              <TypedBubble question={exchange.question} />
            ) : (
              <VoiceBubble exchange={exchange} />
            )}
            <AgentBubble exchange={exchange} />
          </div>
        ))}
        {pendingQuestion === null ? null : <TypedBubble question={pendingQuestion} />}
        {thinking ? (
          <AgentFrame>
            <output className="text-body font-bold text-ink-2">{en.talk.thinking}</output>
          </AgentFrame>
        ) : null}
        <div ref={end} />
      </main>
      <ChatBar control={control} unavailable={view.unavailable} showHint={count === 0} />
    </>
  );
}
