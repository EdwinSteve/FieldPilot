import { useEffect, useState } from "react";
import { ApiError } from "../../api/client";
import { BigButton, BigLink } from "../../farmer/components/BigButton";
import { Icon } from "../../farmer/components/Icon";
import { cop } from "../../farmer/lib/listing";
import avatar from "../../farmer/assets/avatar.webp";
import { CropArt } from "../../farmer/components/CropArt";
import { cropLabel } from "../../farmer/lib/names";
import { store, type CartLine, type CartSuggestion } from "../api/store";
import { AddressField, Empty, KgStepper, Notice } from "../components";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import { addressProblem, kgProblem, labelOfName } from "../lib/shop";
import { cartStore, markPlaced, refreshCart, showToast, useCart, useUser } from "../state";

/** "Updated" stays until the shopper changes that line again or leaves the cart. */
type LineState = "saving" | "updated" | "failed";

/** How long a removed line takes to fade away before the cart closes the gap. */
const LEAVE_MS = 200;
const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/** Undo of a removed line: lives outside the screen, as the toast may outlast it. */
async function putBack(listingId: number, kg: number): Promise<void> {
  try {
    cartStore.set(await store.setItem(listingId, kg));
  } catch {
    showToast({ tone: "needs", text: en.toast.undoFailed });
  }
}

/**
 * The assistant's idea for the cart (D087), as a side note: it never stands between the shopper
 * and Pay. A failed read just shows nothing; No thanks hides it for this visit.
 */
function Suggestion({ cartKey }: { cartKey: string }) {
  const [shown, setShown] = useState<CartSuggestion | null>(null);
  const [closed, setClosed] = useState(false);
  const [busy, setBusy] = useState(false);
  /** Set after "a better deal": then even "that is the best deal" is worth saying. */
  const [searched, setSearched] = useState(false);
  // Read again whenever the cart changes: an added crop is never suggested twice.
  useEffect(() => {
    // An empty cart has nothing to go with: no idea to show.
    if (cartKey === "") return undefined;
    let live = true;
    void store
      .suggestion()
      .then((next) => {
        if (!live) return;
        setShown(next);
        setSearched(false);
      })
      .catch(() => live && setShown(null));
    return () => {
      live = false;
    };
  }, [cartKey]);
  // Nothing to suggest at first: no card at all, rather than "your cart looks complete".
  if (closed || shown === null || (shown.recommendation === null && !searched)) return null;
  const pick = shown.recommendation;
  const run = async (action: CartSuggestion["actions"][number]) => {
    setBusy(true);
    try {
      if (action.kind === "add_to_cart") {
        cartStore.set(await store.setItem(action.listing_id, action.quantity_kg));
        showToast({
          tone: "good",
          text: en.cart.suggestionAdded(action.quantity_kg, pick === null ? "" : cropLabel(pick.product.crop)),
        });
      } else {
        setShown(await store.suggestion(action.exclude));
        setSearched(true);
      }
    } catch {
      // A side note: if it fails, the cart is as it was and Pay still works.
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="flex animate-screen-in flex-col gap-3 rounded-card border-2 border-dashed border-border bg-surface p-4.5">
      {/* The FieldPilot shopping assistant speaking: its face, its name, and an AI badge. */}
      <div className="flex items-start justify-between gap-2">
        <span className="flex items-center gap-2.5">
          <img src={avatar} alt="" width={44} height={44} className="size-11 shrink-0 rounded-full bg-tint object-contain" />
          <span className="flex flex-col">
            <span className="flex flex-wrap items-center gap-x-1.5 text-body font-extrabold whitespace-nowrap">
              {en.cart.assistantName}
              <span className="rounded-pill bg-primary px-1.5 py-0.5 text-caption leading-none font-extrabold text-surface">
                {en.cart.aiBadge}
              </span>
            </span>
            <span className="text-caption font-semibold text-ink-3">{en.cart.suggestionTitle}</span>
          </span>
        </span>
        <button
          type="button"
          onClick={() => setClosed(true)}
          className="press -mt-2 -mr-2 flex min-h-12 shrink-0 items-center rounded-control border-0 bg-transparent px-3 text-small font-bold whitespace-nowrap text-ink-2"
        >
          {en.cart.suggestionLater}
        </button>
      </div>
      <p className="ml-6 rounded-[20px] rounded-tl-md bg-tint px-4 py-3 text-body leading-snug">{shown.message}</p>
      {shown.actions.length === 0 ? null : (
        <div className="flex flex-wrap gap-2">
          {shown.actions.map((action) => (
            <button
              key={action.kind}
              type="button"
              disabled={busy}
              onClick={() => void run(action)}
              className={`press flex min-h-12 items-center rounded-control px-4 text-small font-extrabold disabled:opacity-40 ${
                action.kind === "add_to_cart" ? "border-0 bg-tint text-primary-hover" : "border-2 border-border bg-surface text-ink"
              }`}
            >
              {action.kind === "add_to_cart" && pick !== null ? (
                <span className="mr-2 -ml-1 flex size-8 items-center justify-center rounded-full bg-surface">
                  <CropArt crop={pick.product.crop} size={24} />
                </span>
              ) : null}
              {action.label}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

function LineStatus({ state }: { state: LineState | undefined }) {
  return (
    <span aria-live="polite" className="-mt-1 flex min-h-6 items-center gap-1.5 text-small font-bold">
      {state === "saving" ? <span className="text-ink-3">{en.cart.saving}</span> : null}
      {state === "updated" ? (
        <span className="flex animate-fade-in items-center gap-1 text-primary">
          <Icon name="check" size={18} strokeWidth={2.8} />
          {en.cart.updated}
        </span>
      ) : null}
    </span>
  );
}

export function CartPage() {
  const user = useUser();
  const cart = useCart();
  const [address, setAddress] = useState<string | null>(null);
  /** The address being typed, while its box is open: Pay uses it as typed. */
  const [draft, setDraft] = useState<string | null>(null);
  const [tried, setTried] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  /** Lines whose kilos box the shopper emptied: kept here, never sent, until a number is typed. */
  const [emptied, setEmptied] = useState<ReadonlySet<number>>(() => new Set());
  /** What each line's last change is doing: saving, just saved, or failed. */
  const [lines, setLines] = useState<ReadonlyMap<number, LineState>>(() => new Map());
  /** The line fading out after Remove, so the shopper sees which one went. */
  const [leaving, setLeaving] = useState<number | null>(null);

  // The cart is repriced on every read (§9.3): read it whenever this screen opens.
  useEffect(() => {
    void refreshCart();
  }, []);
  useEffect(() => {
    if (user?.role !== "customer") return;
    void store
      .profile()
      .then((profile) => setAddress((current) => current ?? profile.delivery_address ?? ""))
      .catch(() => setAddress((current) => current ?? ""));
  }, [user?.role]);

  if (user?.role !== "customer") {
    return (
      <Empty icon="bag" title={en.account.signInFirst}>
        <BigLink variant="primary" size="compact" href={hrefOf({ screen: "account" })}>
          <span className="px-6">{en.account.logIn}</span>
        </BigLink>
      </Empty>
    );
  }
  if (cart === null) return <p className="text-body text-ink-2">{en.state.loading}</p>;
  if (cart.lines.length === 0) {
    return (
      <Empty icon="bag" title={en.cart.empty} detail={en.cart.emptyLead}>
        <BigLink variant="primary" size="compact" href={hrefOf({ screen: "shop" })}>
          <span className="px-6">{en.cart.goShop}</span>
        </BigLink>
      </Empty>
    );
  }

  const mark = (listingId: number, state: LineState | null) =>
    setLines((current) => {
      const next = new Map(current);
      if (state === null) next.delete(listingId);
      else next.set(listingId, state);
      return next;
    });
  const markEmptied = (listingId: number, isEmpty: boolean) =>
    setEmptied((current) => {
      const next = new Set(current);
      if (isEmpty) next.add(listingId);
      else next.delete(listingId);
      return next;
    });
  const typeKg = (listingId: number, kg: number | null) => {
    const isEmpty = kgProblem(kg) !== null;
    markEmptied(listingId, isEmpty);
    if (isEmpty) mark(listingId, null);
    else if (kg !== null) void setKg(listingId, kg);
  };
  const remove = async (line: CartLine) => {
    markEmptied(line.listing_id, false);
    mark(line.listing_id, "saving");
    setLeaving(line.listing_id);
    try {
      const [next] = await Promise.all([store.setItem(line.listing_id, 0), wait(LEAVE_MS)]);
      cartStore.set(next);
      setLeaving(null);
      mark(line.listing_id, null);
      const kg = line.quantity_kg;
      showToast({
        tone: "good",
        text: en.toast.removed(labelOfName(line.crop_name)),
        action: { label: en.toast.undo, run: () => void putBack(line.listing_id, kg) },
      });
    } catch {
      setLeaving(null);
      mark(line.listing_id, null);
      showToast({ tone: "needs", text: en.toast.removeFailed });
    }
  };
  const anyEmpty = cart.lines.some((line) => emptied.has(line.listing_id));
  const setKg = async (listingId: number, kg: number) => {
    mark(listingId, "saving");
    try {
      cartStore.set(await store.setItem(listingId, kg));
      mark(listingId, "updated");
    } catch {
      mark(listingId, "failed");
    }
  };
  const text = draft ?? address ?? "";
  const problem = addressProblem(text);
  const pay = async () => {
    setTried(true);
    setFailure(null);
    if (problem !== null || !cart.can_checkout || anyEmpty) return;
    setBusy(true);
    try {
      const order = await store.checkout(text.trim());
      await refreshCart();
      markPlaced(order.id);
      window.location.hash = hrefOf({ screen: "order", id: order.id });
    } catch (caught) {
      const code = caught instanceof ApiError ? caught.code : "other";
      setFailure(en.cart.failures[code] ?? en.cart.failures.other ?? null);
      await refreshCart();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
      <section className="flex flex-col gap-3">
        <h1 className="text-title font-extrabold tracking-title">{en.cart.title}</h1>
        {cart.lines.map((line) => (
          <article
            key={line.listing_id}
            className={`flex animate-screen-in flex-col gap-3 rounded-card bg-surface p-4.5 transition-[opacity,scale] duration-200 ease-(--ease-calm) ${
              leaving === line.listing_id ? "scale-95 opacity-0" : ""
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex flex-col">
                <a href={hrefOf({ screen: "product", id: line.listing_id })} className="text-row font-extrabold text-ink no-underline">
                  {labelOfName(line.crop_name)}
                </a>
                <span className="text-small text-ink-2">{en.cart.line(line.quantity_kg, cop(line.unit_price_cop))}</span>
              </div>
              <span className="text-row font-extrabold">{cop(line.line_total_cop)}</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <KgStepper
                kg={emptied.has(line.listing_id) ? null : line.quantity_kg}
                max={Math.floor(line.available_kg)}
                onChange={(kg) => typeKg(line.listing_id, kg)}
                of={Math.floor(line.available_kg)}
              />
              <button
                type="button"
                aria-label={en.cart.remove(labelOfName(line.crop_name))}
                disabled={lines.get(line.listing_id) === "saving"}
                onClick={() => void remove(line)}
                className="press flex size-12 items-center justify-center rounded-control border-0 bg-transparent text-bad-text disabled:opacity-40"
              >
                <Icon name="close" size={24} strokeWidth={2.6} />
              </button>
            </div>
            {/* Its own line, its height kept: "Updated" never pushes the row wider on a phone. */}
            <LineStatus state={lines.get(line.listing_id)} />
            {emptied.has(line.listing_id) ? <Notice text={en.cart.typeKg} /> : null}
            {lines.get(line.listing_id) === "failed" ? <Notice text={en.cart.lineFailed} /> : null}
            {line.problem === null ? null : <Notice text={en.cart.problems[line.problem]} />}
          </article>
        ))}
        <Suggestion cartKey={cart.lines.map((line) => `${line.listing_id}:${line.quantity_kg}`).join(",")} />
      </section>
      <aside className="flex h-fit flex-col gap-4 rounded-card bg-surface p-5 lg:sticky lg:top-24">
        <div className="flex items-baseline justify-between">
          <span className="text-lead font-bold">{en.cart.total}</span>
          <span className="text-[32px] font-extrabold tracking-key">{cop(cart.total_cop)}</span>
        </div>
        {address === null ? (
          <p className="text-body text-ink-2">{en.state.loading}</p>
        ) : (
          <AddressField
            label={en.cart.address}
            hint={en.cart.addressHint}
            saved={address}
            confirmLabel={en.cart.confirmAddress}
            changeLabel={en.cart.changeAddress}
            showProblem={tried}
            // For this order only: the saved address in Account stays as it is.
            onConfirm={(next) => {
              setAddress(next);
              return true;
            }}
            onDraft={setDraft}
          />
        )}
        {cart.can_checkout && !anyEmpty ? null : <Notice text={en.cart.fix} />}
        {failure === null ? null : <Notice text={failure} />}
        <BigButton variant="primary" disabled={busy || !cart.can_checkout || anyEmpty} onClick={() => void pay()}>
          <Icon name="lock" size={22} />
          {busy ? en.cart.paying : `${en.cart.pay} ${cop(cart.total_cop)}`}
        </BigButton>
        <p className="text-small text-ink-3">{en.cart.mock}</p>
      </aside>
    </div>
  );
}
