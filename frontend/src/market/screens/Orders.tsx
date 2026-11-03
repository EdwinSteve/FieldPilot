import { useCallback, useState } from "react";
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
import { useUser, wasJustPlaced } from "../state";

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

function OrderCard({ order, open }: { order: Order; open?: boolean }) {
  return (
    <article className="flex flex-col gap-3 rounded-card bg-surface p-5">
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
      ) : (
        <span className="text-small text-ink-2">{order.lines.map((line) => `${cropLabel(line.crop)} ${line.quantity_kg} kg`).join(" · ")}</span>
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
  if (user?.role !== "customer") return <SignIn />;
  if (order.data === null) {
    return order.error === null ? <p className="text-body text-ink-2">{en.state.loading}</p> : <Empty icon="document" title={en.orders.notFound} />;
  }
  const o = order.data;
  const cancel = async () => {
    setBusy(true);
    try {
      await store.cancel(o.id);
      setVersion((v) => v + 1);
    } finally {
      setBusy(false);
      setAsking(false);
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
