import { useCallback, useId, useState } from "react";
import { ApiError } from "../../api/client";
import { useResource } from "../../hooks/useResource";
import { BigButton, BigLink } from "../../farmer/components/BigButton";
import { Icon } from "../../farmer/components/Icon";
import { formatCalendarDate } from "../../farmer/lib/farmTime";
import { cop } from "../../farmer/lib/listing";
import { cropLabel } from "../../farmer/lib/names";
import { store, type Order, type OrderStatus } from "../api/store";
import { Empty, Notice } from "../components";
import { en } from "../i18n/en";
import { hrefOf, lotHref } from "../lib/route";
import { failureWords } from "../lib/shop";
import { showToast, useUser, wasJustPlaced } from "../state";

const loadOrders = () => store.orders();

const STATUS_STYLE: Record<OrderStatus, string> = {
  paid: "bg-undo-tint text-undo-text",
  delivered: "bg-tint text-primary-hover",
  cancelled: "bg-ground text-ink-3",
};
const STATUS_ICON = { paid: "clock", delivered: "check", cancelled: "close" } as const;

function Status({ status }: { status: OrderStatus }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-pill px-3 py-1 text-small font-bold ${STATUS_STYLE[status]}`}>
      <Icon name={STATUS_ICON[status]} size={16} strokeWidth={2.6} />
      {en.orders.status[status]}
    </span>
  );
}

function OrderLines({ order }: { order: Order }) {
  return (
    <ul className="flex flex-col divide-y divide-divider">
      {order.lines.map((line) => (
        <li key={line.listing_id} className="flex items-center justify-between gap-3 py-2.5">
          <div className="flex flex-col">
            <span className="text-body font-bold">
              {cropLabel(line.crop)} · {line.quantity_kg} kg
            </span>
            <a href={lotHref(line.passport_path)} className="font-mono text-caption text-primary">
              {en.orders.passport} {line.lot_code}
            </a>
          </div>
          <span className="text-body font-extrabold">{cop(line.line_total_cop)}</span>
        </li>
      ))}
    </ul>
  );
}

/** On the order's own page the lines always show; in the list they open in place under More details. */
function OrderCard({ order, open }: { order: Order; open?: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const id = useId();
  return (
    <article className="flex animate-screen-in flex-col gap-3 rounded-card bg-surface p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <a href={hrefOf({ screen: "order", id: order.id })} className="text-row font-extrabold text-ink no-underline">
          {en.orders.number(order.id)}
        </a>
        <Status status={order.status} />
      </div>
      <span className="text-small text-ink-2">
        {en.orders.placed(formatCalendarDate(order.placed_at.slice(0, 10)))} · {cop(order.total_cop)}
      </span>
      {open ? (
        <OrderLines order={order} />
      ) : (
        <>
          {/* The one-line summary gives way to the full lines once they are open. */}
          {expanded ? null : (
            <span className="animate-fade-in text-small text-ink-2">
              {order.lines.map((line) => `${cropLabel(line.crop)} ${line.quantity_kg} kg`).join(" · ")}
            </span>
          )}
          <div
            id={id}
            inert={!expanded}
            className={`grid transition-[grid-template-rows,opacity,visibility] duration-300 ease-(--ease-calm) ${
              expanded ? "grid-rows-[1fr] opacity-100" : "invisible grid-rows-[0fr] opacity-0"
            }`}
          >
            <div className="min-h-0 overflow-hidden">
              <OrderLines order={order} />
            </div>
          </div>
          <button
            type="button"
            aria-expanded={expanded}
            aria-controls={id}
            onClick={() => setExpanded((current) => !current)}
            className="press -ml-1 flex min-h-12 items-center gap-2 self-start rounded-control border-0 bg-transparent px-1 text-body font-bold text-primary"
          >
            {expanded ? en.orders.fewerDetails : en.orders.moreDetails}
            <Icon
              name="chevronDown"
              size={20}
              strokeWidth={2.6}
              className={`transition-transform duration-300 ease-(--ease-calm) ${expanded ? "rotate-180" : ""}`}
            />
          </button>
        </>
      )}
    </article>
  );
}

export function OrdersPage() {
  const user = useUser();
  const orders = useResource(user?.role === "customer" ? loadOrders : none, 0);
  if (user?.role !== "customer") return <SignIn />;
  const list = orders.data ?? [];
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-title font-extrabold tracking-title">{en.orders.title}</h1>
      {orders.data === null ? (
        <p className="text-body text-ink-2">{en.state.loading}</p>
      ) : list.length === 0 ? (
        <Empty icon="document" title={en.orders.empty}>
          <BigLink variant="primary" size="compact" href={hrefOf({ screen: "shop" })}>
            <span className="px-6">{en.cart.goShop}</span>
          </BigLink>
        </Empty>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {list.map((order) => (
            <OrderCard key={order.id} order={order} />
          ))}
        </div>
      )}
    </div>
  );
}

const none = () => Promise.resolve([]);

export function OrderPage({ id }: { id: number }) {
  const user = useUser();
  const [version, setVersion] = useState(0);
  const order = useResource(
    useCallback(() => store.order(id), [id]),
    version,
  );
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [cancelFailed, setCancelFailed] = useState<string | null>(null);
  if (user?.role !== "customer") return <SignIn />;
  if (order.data === null) {
    return order.error === null ? <p className="text-body text-ink-2">{en.state.loading}</p> : <Empty icon="document" title={en.orders.notFound} />;
  }
  const o = order.data;
  const cancel = async () => {
    setBusy(true);
    setCancelFailed(null);
    try {
      await store.cancel(o.id);
      setVersion((v) => v + 1);
      setAsking(false);
      showToast({ tone: "good", text: en.toast.cancelled(o.id) });
    } catch (caught) {
      setCancelFailed(failureWords(en.orders.cancelFailed, caught instanceof ApiError ? caught.code : null));
      // It may have been delivered meanwhile: show the order as it is now.
      setVersion((v) => v + 1);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-4">
      {wasJustPlaced(o.id) ? (
        <section className="flex animate-card-in flex-col items-center gap-3 rounded-[32px] bg-tint px-6 py-8 text-center text-primary-hover">
          <span className="flex size-20 animate-pop-in items-center justify-center rounded-full bg-primary text-surface">
            <Icon name="check" size={44} strokeWidth={3} />
          </span>
          <h1 className="text-title font-extrabold tracking-title">{en.orders.thanks}</h1>
          <p className="max-w-md text-body text-ink-2">{en.orders.thanksLead}</p>
        </section>
      ) : (
        <h1 className="text-title font-extrabold tracking-title">{en.orders.number(o.id)}</h1>
      )}
      <OrderCard order={o} open />
      <div className="flex flex-col gap-1 px-1 text-small text-ink-2">
        {o.delivery_address === null ? null : <span>{en.orders.deliverTo(o.delivery_address)}</span>}
        <span className="font-mono">{en.orders.payment(o.payment_ref)}</span>
      </div>
      {cancelFailed === null ? null : <Notice text={cancelFailed} />}
      {o.status === "paid" ? (
        asking ? (
          <div className="flex flex-col gap-3 rounded-card bg-surface p-5">
            <Notice text={en.orders.cancelAsk} />
            <BigButton variant="outline" size="compact" onClick={() => setAsking(false)}>
              {en.orders.keep}
            </BigButton>
            <BigButton variant="primary" size="compact" disabled={busy} onClick={() => void cancel()}>
              {busy ? en.orders.cancelling : en.orders.confirmCancel}
            </BigButton>
          </div>
        ) : (
          <BigButton variant="outline" size="compact" onClick={() => setAsking(true)}>
            {en.orders.cancel}
          </BigButton>
        )
      ) : null}
    </div>
  );
}

function SignIn() {
  return (
    <Empty icon="lock" title={en.account.signInFirst}>
      <BigLink variant="primary" size="compact" href={hrefOf({ screen: "account" })}>
        <span className="px-6">{en.account.logIn}</span>
      </BigLink>
    </Empty>
  );
}
