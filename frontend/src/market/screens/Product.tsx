import { useCallback, useState } from "react";
import { useResource } from "../../hooks/useResource";
import { BigButton, BigLink } from "../../farmer/components/BigButton";
import { CropArt } from "../../farmer/components/CropArt";
import { Icon } from "../../farmer/components/Icon";
import { formatCalendarDate } from "../../farmer/lib/farmTime";
import { kgText } from "../../farmer/lib/harvest";
import { cop } from "../../farmer/lib/listing";
import { cropLabel } from "../../farmer/lib/names";
import { store } from "../api/store";
import { Empty, Journey, KgStepper, Notice, PriceSplit, ShareBar, Verified } from "../components";
import { en } from "../i18n/en";
import { hrefOf, lotHref } from "../lib/route";
import { clampKg } from "../lib/shop";
import { cartStore, useCart, useUser } from "../state";

export function ProductPage({ id }: { id: number }) {
  const user = useUser();
  const cart = useCart();
  const product = useResource(
    useCallback(() => store.product(id), [id]),
    0,
  );
  const code = product.data?.lot_code ?? null;
  const passport = useResource(
    useCallback(() => (code === null ? Promise.resolve(null) : store.passport(code)), [code]),
    0,
  );
  const [kg, setKg] = useState(1);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const inCart = cart?.lines.find((line) => line.listing_id === id)?.quantity_kg ?? 0;

  if (product.data === null) {
    return product.error === null ? (
      <p className="text-body text-ink-2">{en.state.loading}</p>
    ) : (
      <Empty icon="bag" title={en.product.notFound}>
        <BigLink variant="outline" size="compact" href={hrefOf({ screen: "shop" })}>
          <span className="px-4">{en.product.back}</span>
        </BigLink>
      </Empty>
    );
  }
  const p = product.data;
  const max = Math.floor(p.available_kg);

  const add = async () => {
    setBusy(true);
    setFailed(false);
    try {
      cartStore.set(await store.setItem(p.id, clampKg(inCart + kg, max)));
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <a href={hrefOf({ screen: "shop" })} className="inline-flex min-h-12 items-center gap-2 self-start text-body font-bold text-primary no-underline">
        <Icon name="back" size={22} strokeWidth={2.4} />
        {en.product.back}
      </a>
      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <div className="flex flex-col gap-5">
          <div className="relative flex h-72 items-center justify-center rounded-[32px] bg-tint md:h-96">
            <CropArt crop={p.crop} size={200} />
            {p.offer === null ? null : (
              <span className="absolute top-5 left-5 rounded-pill bg-needs px-4 py-2 text-body font-extrabold text-surface">
                {en.product.off(p.offer.discount_pct)}
              </span>
            )}
          </div>
          <PriceSplit price={p.price} />
        </div>
        <div className="flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <h1 className="text-[40px] leading-tight font-extrabold tracking-title">{cropLabel(p.crop)}</h1>
            <p className="text-lead text-ink-2">{p.producer}</p>
            <div className="flex items-baseline gap-2">
              <span className="text-[36px] font-extrabold tracking-key">{cop(p.price.total_cop)}</span>
              <span className="text-body text-ink-3">{en.product.perKg}</span>
            </div>
            <ShareBar price={p.price} />
          </div>
          <ul className="flex flex-col gap-2 text-body text-ink-2">
            <li className="flex items-center gap-2">
              <Icon name="calendar" size={20} className="text-primary" />
              {en.product.harvested(formatCalendarDate(p.harvested_on))} · {en.product.bestBefore(formatCalendarDate(p.best_before))}
            </li>
            <li className="flex items-center gap-2">
              <Icon name="home" size={20} className="text-primary" />
              {en.product.warehouse(p.warehouse)}
            </li>
            <li className="flex items-center gap-2">
              <Icon name="bag" size={20} className="text-primary" />
              {en.product.left(kgText(p.available_kg))}
            </li>
            {p.offer === null ? null : (
              <li className="flex items-center gap-2 font-bold text-needs-text">
                <Icon name="clock" size={20} />
                {en.product.offerEnds(formatCalendarDate(p.offer.ends_on))}
              </li>
            )}
          </ul>
          <div className="sticky bottom-24 z-10 flex flex-col gap-3 rounded-card bg-surface p-5 shadow-[0_12px_40px_rgba(21,39,40,0.12)] md:bottom-4">
            {user?.role === "customer" ? (
              <>
                <KgStepper kg={kg} max={Math.max(1, max - inCart)} onChange={(next) => setKg(Math.max(1, clampKg(next, max - inCart)))} />
                <BigButton variant="primary" disabled={busy || max - inCart <= 0} onClick={() => void add()}>
                  <Icon name="bag" size={24} />
                  {busy ? en.product.adding : `${en.product.add} · ${cop(p.price.total_cop * kg)}`}
                </BigButton>
                {inCart > 0 ? (
                  <a href={hrefOf({ screen: "cart" })} className="text-center text-body font-bold text-primary">
                    {en.product.added(inCart)} · {en.product.viewCart}
                  </a>
                ) : null}
                {failed ? <Notice text={en.cart.failures.other ?? ""} /> : null}
              </>
            ) : (
              <BigLink variant="primary" href={hrefOf({ screen: "account" })}>
                {en.product.signInToBuy}
              </BigLink>
            )}
          </div>
          <section className="flex flex-col gap-3 rounded-card bg-surface p-5">
            <h2 className="text-lead font-extrabold">{en.product.passport}</h2>
            {passport.data === null ? (
              <p className="text-body text-ink-2">{en.state.loading}</p>
            ) : (
              <>
                <Verified verified={passport.data.integrity.verified} />
                <Journey passport={passport.data} />
              </>
            )}
            <a href={lotHref(p.passport_path)} className="inline-flex min-h-12 items-center gap-2 text-body font-bold text-primary">
              {en.product.fullPassport}
              <span className="font-mono text-small text-ink-3">{p.lot_code}</span>
            </a>
          </section>
        </div>
      </div>
    </div>
  );
}
