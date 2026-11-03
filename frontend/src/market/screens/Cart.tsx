import { useEffect, useState } from "react";
import { ApiError } from "../../api/client";
import { BigButton, BigLink } from "../../farmer/components/BigButton";
import { Icon } from "../../farmer/components/Icon";
import { TextField } from "../../farmer/components/TextField";
import { cop } from "../../farmer/lib/listing";
import { store } from "../api/store";
import { Empty, KgStepper, Notice } from "../components";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import { addressProblem, clampKg, labelOfName } from "../lib/shop";
import { cartStore, markPlaced, refreshCart, useCart, useUser } from "../state";

export function CartPage() {
  const user = useUser();
  const cart = useCart();
  const [address, setAddress] = useState<string | null>(null);
  const [tried, setTried] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

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

  const setKg = async (listingId: number, kg: number) => {
    try {
      cartStore.set(await store.setItem(listingId, kg));
    } catch {
      setFailure(en.cart.failures.other ?? null);
    }
  };
  const text = address ?? "";
  const problem = addressProblem(text);
  const pay = async () => {
    setTried(true);
    setFailure(null);
    if (problem !== null || !cart.can_checkout) return;
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
          <article key={line.listing_id} className="flex flex-col gap-3 rounded-card bg-surface p-4.5">
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
                kg={line.quantity_kg}
                max={Math.floor(line.available_kg)}
                onChange={(kg) => void setKg(line.listing_id, Math.max(1, clampKg(kg, line.available_kg)))}
              />
              <button
                type="button"
                aria-label={en.cart.remove(labelOfName(line.crop_name))}
                onClick={() => void setKg(line.listing_id, 0)}
                className="press flex size-12 items-center justify-center rounded-control border-0 bg-transparent text-bad-text"
              >
                <Icon name="close" size={24} strokeWidth={2.6} />
              </button>
            </div>
            {line.problem === null ? null : <Notice text={en.cart.problems[line.problem]} />}
          </article>
        ))}
      </section>
      <aside className="flex h-fit flex-col gap-4 rounded-card bg-surface p-5 lg:sticky lg:top-24">
        <div className="flex items-baseline justify-between">
          <span className="text-lead font-bold">{en.cart.total}</span>
          <span className="text-[32px] font-extrabold tracking-key">{cop(cart.total_cop)}</span>
        </div>
        <TextField
          label={en.cart.address}
          hint={en.cart.addressHint}
          value={text}
          onChange={setAddress}
          problem={tried && problem !== null ? en.cart.addressProblem : null}
          autoComplete="street-address"
        />
        {cart.can_checkout ? null : <Notice text={en.cart.fix} />}
        {failure === null ? null : <Notice text={failure} />}
        <BigButton variant="primary" disabled={busy || !cart.can_checkout} onClick={() => void pay()}>
          <Icon name="lock" size={22} />
          {busy ? en.cart.paying : `${en.cart.pay} ${cop(cart.total_cop)}`}
        </BigButton>
        <p className="text-small text-ink-3">{en.cart.mock}</p>
      </aside>
    </div>
  );
}
