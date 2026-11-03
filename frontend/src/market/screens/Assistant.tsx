import { useState } from "react";
import { ApiError } from "../../api/client";
import { BigButton, BigLink } from "../../farmer/components/BigButton";
import { Icon } from "../../farmer/components/Icon";
import { store, type AssistantAnswer } from "../api/store";
import { Empty, Notice } from "../components";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import { cartStore, useUser } from "../state";

interface Turn {
  question: string;
  answer: AssistantAnswer | null;
  /** Why there is no answer: the model is off, or the call failed. */
  failed: "unavailable" | "failed" | null;
}

export function AssistantPage() {
  const user = useUser();
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [accepted, setAccepted] = useState<Set<number>>(() => new Set());

  if (user?.role !== "customer") {
    return (
      <Empty icon="chat" title={en.assistant.signIn}>
        <BigLink variant="primary" size="compact" href={hrefOf({ screen: "account" })}>
          <span className="px-6">{en.account.logIn}</span>
        </BigLink>
      </Empty>
    );
  }

  const ask = async () => {
    const question = draft.trim();
    if (question === "" || busy) return;
    setDraft("");
    setBusy(true);
    setTurns((current) => [...current, { question, answer: null, failed: null }]);
    let turn: Turn;
    try {
      turn = { question, answer: await store.ask(question), failed: null };
    } catch (caught) {
      turn = { question, answer: null, failed: caught instanceof ApiError && caught.status === 503 ? "unavailable" : "failed" };
    }
    setTurns((current) => [...current.slice(0, -1), turn]);
    setBusy(false);
  };

  const accept = async (proposalId: number) => {
    cartStore.set(await store.accept(proposalId));
    setAccepted((current) => new Set(current).add(proposalId));
  };

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <header className="flex flex-col gap-2">
        <span className="text-small font-extrabold tracking-[0.14em] text-primary">{en.assistant.builtOn.toUpperCase()}</span>
        <h1 className="text-title font-extrabold tracking-title">{en.assistant.title}</h1>
        <p className="text-lead leading-snug text-ink-2">{en.assistant.lead}</p>
      </header>
      <ol className="flex flex-col gap-4">
        {turns.map((turn, i) => (
          <li key={i} className="flex flex-col gap-3">
            <p className="max-w-[85%] self-end rounded-[22px] rounded-br-md bg-primary px-4 py-3 text-body text-surface">{turn.question}</p>
            {turn.answer === null && turn.failed === null ? (
              <p className="self-start rounded-[22px] bg-surface px-4 py-3 text-body text-ink-2">{en.assistant.asking}</p>
            ) : null}
            {turn.failed === null ? null : <Notice text={turn.failed === "unavailable" ? en.assistant.unavailable : en.assistant.failed} />}
            {turn.answer === null ? null : (
              <div className="flex max-w-[90%] flex-col gap-3 self-start rounded-[22px] rounded-bl-md bg-surface px-4 py-3">
                <p className="text-body leading-snug whitespace-pre-line">{turn.answer.answer}</p>
                {turn.answer.proposal === null ? null : (
                  <div className="flex flex-col gap-2 rounded-control bg-tint p-3">
                    <span className="text-small font-extrabold text-primary-hover">{en.assistant.proposal}</span>
                    <p className="text-small text-ink-2">{turn.answer.proposal.note}</p>
                    {accepted.has(turn.answer.proposal.id) ? (
                      <Notice tone="good" text={en.assistant.added} />
                    ) : (
                      <BigButton variant="primary" size="compact" onClick={() => void accept(turn.answer!.proposal!.id)}>
                        <Icon name="bag" size={22} />
                        {en.assistant.addAll}
                      </BigButton>
                    )}
                  </div>
                )}
              </div>
            )}
          </li>
        ))}
      </ol>
      <form
        className="sticky bottom-24 flex gap-2 rounded-card bg-surface p-3 shadow-[0_12px_40px_rgba(21,39,40,0.12)] md:bottom-4"
        onSubmit={(event) => {
          event.preventDefault();
          void ask();
        }}
      >
        <label className="flex flex-1">
          <span className="sr-only">{en.assistant.title}</span>
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value.slice(0, 500))}
            placeholder={en.assistant.placeholder}
            className="min-h-14 w-full rounded-control border-2 border-border bg-ground px-4 text-body text-ink"
          />
        </label>
        <button type="submit" disabled={busy} className="press min-h-14 rounded-control bg-primary px-6 text-body font-extrabold text-surface disabled:opacity-50">
          {busy ? en.assistant.asking : en.assistant.ask}
        </button>
      </form>
    </div>
  );
}
