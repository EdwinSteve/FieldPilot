import { useState } from "react";
import { BigButton, BigLink } from "../../farmer/components/BigButton";
import { Icon } from "../../farmer/components/Icon";
import { Empty, Notice } from "../components";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import { acceptProposal, askAssistant, useChat, useUser } from "../state";

export function AssistantPage() {
  const user = useUser();
  const { turns, accepted, busy } = useChat();
  const [draft, setDraft] = useState("");
  const [acceptFailed, setAcceptFailed] = useState(false);

  if (user?.role !== "customer") {
    return (
      <Empty icon="chat" title={en.assistant.signIn}>
        <BigLink variant="primary" size="compact" href={hrefOf({ screen: "account" })}>
          <span className="px-6">{en.account.logIn}</span>
        </BigLink>
      </Empty>
    );
  }

  const ask = () => {
    const question = draft.trim();
    if (question === "" || busy) return;
    setDraft("");
    void askAssistant(question);
  };

  const accept = async (proposalId: number) => {
    setAcceptFailed(false);
    try {
      await acceptProposal(proposalId);
    } catch {
      setAcceptFailed(true);
    }
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
                <p className={`text-body leading-snug whitespace-pre-line ${turn.answer.answer === null ? "text-ink-2" : ""}`}>
                  {turn.answer.answer ?? en.assistant.noAnswer}
                </p>
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
                    {acceptFailed && !accepted.has(turn.answer.proposal.id) ? <Notice text={en.assistant.failed} /> : null}
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
          ask();
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
