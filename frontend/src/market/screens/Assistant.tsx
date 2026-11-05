import { useCallback, useState } from "react";
import { useResource } from "../../hooks/useResource";
import { CropArt } from "../../farmer/components/CropArt";
import { cop } from "../../farmer/lib/listing";
import { cropLabel } from "../../farmer/lib/names";
import { store, type Proposal } from "../api/store";
import { isClearance, withoutReasonCodes } from "../lib/shop";
import { BigButton, BigLink } from "../../farmer/components/BigButton";
import { Icon } from "../../farmer/components/Icon";
import { Empty, Notice } from "../components";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import { acceptProposal, askAssistant, useChat, useUser } from "../state";

/**
 * The proposed cart as small product cards: picture, kilos and price, and why it is cheaper.
 * Read from the store by listing; a product that cannot be read is simply left out.
 */
function ProposalItems({ proposal }: { proposal: Proposal }) {
  const ids = proposal.items.map((item) => item.listing_id).join(",");
  const products = useResource(
    useCallback(
      () => Promise.all(proposal.items.map((item) => store.product(item.listing_id).catch(() => null))),
      // The items of one proposal never change: its listing ids say it all.
      // oxlint-disable-next-line react-hooks/exhaustive-deps
      [ids],
    ),
    0,
  );
  return (
    <ul className="flex flex-col gap-2">
      {proposal.items.map((item, index) => {
        const product = products.data?.[index] ?? null;
        if (product === null) return null;
        const total = product.price.total_cop * item.quantity_kg;
        return (
          <li key={item.listing_id} className="flex animate-screen-in flex-col gap-2 rounded-tile bg-surface p-3">
            <div className="flex items-center gap-3">
              <span className="flex size-12 shrink-0 items-center justify-center rounded-tile bg-tint">
                <CropArt crop={product.crop} size={34} />
              </span>
              {/* The name, then its badge under it: side by side they collide on a phone. */}
              <span className="flex min-w-0 flex-1 flex-col items-start gap-1">
                <span className="text-body font-extrabold">{cropLabel(product.crop)}</span>
                {product.offer === null ? null : (
                  <span className="rounded-pill bg-needs-tint px-2.5 py-0.5 text-caption font-bold whitespace-nowrap text-needs-text">
                    {isClearance(product)
                      ? en.product.clearanceBadge(product.offer.discount_pct, product.days_left ?? null)
                      : `−${product.offer.discount_pct}%`}
                  </span>
                )}
              </span>
            </div>
            <div className="flex items-baseline justify-between gap-3 border-t border-divider pt-2">
              <span className="text-small whitespace-nowrap text-ink-2">{en.assistant.proposalLine(item.quantity_kg, cop(product.price.total_cop))}</span>
              <span className="text-body font-extrabold whitespace-nowrap">{cop(total)}</span>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

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
              <div
                className={`flex flex-col gap-3 self-start rounded-[22px] rounded-bl-md px-4 py-3 ${
                  turn.answer.proposal === null ? "max-w-[90%]" : "w-full max-w-md"
                } ${
                  turn.answer.topic === "out_of_scope" ? "border-2 border-dashed border-border bg-ground" : "bg-surface"
                }`}
              >
                {/* Off the store's subject: a gentle refusal, the backend's fixed words under a plain title. */}
                {turn.answer.topic === "out_of_scope" ? (
                  <span className="flex items-center gap-2 text-small font-extrabold text-ink-2">
                    <Icon name="info" size={18} strokeWidth={2.4} />
                    {en.assistant.offTopic}
                  </span>
                ) : null}
                <p className={`text-body leading-snug whitespace-pre-line ${turn.answer.answer === null || turn.answer.topic === "out_of_scope" ? "text-ink-2" : ""}`}>
                  {turn.answer.answer === null ? en.assistant.noAnswer : withoutReasonCodes(turn.answer.answer, en.reasons)}
                </p>
                {turn.answer.proposal === null ? null : (
                  <div className="flex flex-col gap-2 rounded-control bg-tint p-3">
                    <span className="text-small font-extrabold text-primary-hover">{en.assistant.proposal}</span>
                    {/* The cards say what is in it; the model's own note ("tomato for customer, 2 kg") says less. */}
                    <ProposalItems proposal={turn.answer.proposal} />
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
