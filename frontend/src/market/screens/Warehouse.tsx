import { useState } from "react";
import { ApiError } from "../../api/client";
import { useResource } from "../../hooks/useResource";
import { BigButton, BigLink } from "../../farmer/components/BigButton";
import { CropArt } from "../../farmer/components/CropArt";
import { TextField } from "../../farmer/components/TextField";
import { kgText } from "../../farmer/lib/harvest";
import { typedWhole } from "../../farmer/lib/listing";
import { cropLabel } from "../../farmer/lib/names";
import { store, type IncomingListing } from "../api/store";
import { Empty, Notice } from "../components";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import { canRunWarehouse } from "../lib/storedUser";
import { useUser } from "../state";

const failureOf = (caught: unknown) =>
  en.warehouse.failures[caught instanceof ApiError ? caught.code : "other"] ?? en.warehouse.failures.other ?? "";

/** Weigh it, note the temperature, receive it: the stock goes on sale. */
function ReceiveForm({ shipmentId, sentKg, onDone }: { shipmentId: number | null; sentKg: number | null; onDone: () => void }) {
  const [number, setNumber] = useState(shipmentId === null ? "" : String(shipmentId));
  const [kg, setKg] = useState(sentKg === null ? "" : String(Math.floor(sentKg)));
  const [temperature, setTemperature] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null);
  const submit = async () => {
    const id = Number(number);
    const weight = Number(kg);
    if (!(id > 0) || !(weight > 0)) return;
    setBusy(true);
    setResult(null);
    try {
      await store.receive(id, weight, temperature === "" ? null : Number(temperature.replace(",", ".")));
      setResult({ ok: true, text: en.warehouse.received(id) });
      onDone();
    } catch (caught) {
      setResult({ ok: false, text: failureOf(caught) });
    } finally {
      setBusy(false);
    }
  };
  return (
    <form
      noValidate
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      {shipmentId === null ? (
        <TextField label={en.warehouse.deliveryNumber} value={number} onChange={(v) => setNumber(typedWhole(v))} problem={null} inputMode="numeric" />
      ) : null}
      <div className="grid gap-3 sm:grid-cols-2">
        <TextField
          label={en.warehouse.receivedKg}
          hint={sentKg === null ? en.warehouse.receivedAny : en.warehouse.receivedHint(kgText(sentKg))}
          value={kg}
          onChange={(v) => setKg(typedWhole(v))}
          problem={null}
          inputMode="numeric"
        />
        <TextField
          label={en.warehouse.temperature}
          hint={en.warehouse.temperatureHint}
          value={temperature}
          onChange={(v) => setTemperature(v.replace(/[^\d.,-]/g, "").slice(0, 5))}
          problem={null}
          inputMode="decimal"
        />
      </div>
      {result === null ? null : <Notice tone={result.ok ? "good" : "needs"} text={result.text} />}
      <BigButton type="submit" variant="primary" size="compact" disabled={busy}>
        {busy ? en.warehouse.receiving : en.warehouse.receive}
      </BigButton>
    </form>
  );
}

function Incoming({ listing, onDone }: { listing: IncomingListing; onDone: () => void }) {
  const shipment = listing.shipment;
  if (shipment === null) return null;
  return (
    <article className="flex flex-col gap-4 rounded-card bg-surface p-5">
      <div className="flex items-center gap-4">
        <span className="flex size-16 shrink-0 items-center justify-center rounded-card bg-tint">
          <CropArt crop={listing.crop} size={48} />
        </span>
        <div className="flex flex-col">
          <span className="text-row font-extrabold">{en.warehouse.delivery(shipment.id)}</span>
          <span className="text-small text-ink-2">{en.warehouse.sent(kgText(shipment.dispatched_kg), cropLabel(listing.crop), listing.lot_code)}</span>
        </div>
      </div>
      <ReceiveForm shipmentId={shipment.id} sentKg={shipment.dispatched_kg} onDone={onDone} />
    </article>
  );
}

function HandOver() {
  const [number, setNumber] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null);
  const submit = async () => {
    const id = Number(number);
    if (!(id > 0)) return;
    setBusy(true);
    setResult(null);
    try {
      await store.deliver(id);
      setResult({ ok: true, text: en.warehouse.delivered(id) });
      setNumber("");
    } catch (caught) {
      setResult({ ok: false, text: failureOf(caught) });
    } finally {
      setBusy(false);
    }
  };
  return (
    <form
      noValidate
      className="flex flex-col gap-3 rounded-card bg-surface p-5"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <h2 className="text-lead font-extrabold">{en.warehouse.handOver}</h2>
      <TextField label={en.warehouse.orderNumber} value={number} onChange={(v) => setNumber(typedWhole(v))} problem={null} inputMode="numeric" />
      {result === null ? null : <Notice tone={result.ok ? "good" : "needs"} text={result.text} />}
      <BigButton type="submit" variant="primary" size="compact" disabled={busy}>
        {busy ? en.warehouse.delivering : en.warehouse.deliver}
      </BigButton>
    </form>
  );
}

const loadListings = () => store.listings();
const noListings = () => Promise.resolve<IncomingListing[]>([]);

/** The warehouse: receive deliveries into stock, hand paid orders over. */
export function WarehousePage() {
  const user = useUser();
  const admin = user?.role === "admin";
  const [version, setVersion] = useState(0);
  const listings = useResource(admin ? loadListings : noListings, version);
  if (!canRunWarehouse(user?.role ?? null)) {
    return (
      <Empty icon="lock" title={en.warehouse.signIn}>
        <BigLink variant="primary" size="compact" href={hrefOf({ screen: "account" })}>
          <span className="px-6">{en.account.logIn}</span>
        </BigLink>
      </Empty>
    );
  }
  const incoming = (listings.data ?? []).filter((listing) => listing.shipment?.status === "dispatched");
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-title font-extrabold tracking-title">{en.warehouse.title}</h1>
        <p className="text-lead text-ink-2">{en.warehouse.lead}</p>
      </header>
      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <section className="flex flex-col gap-3">
          <h2 className="text-lead font-extrabold">{en.warehouse.incoming}</h2>
          {admin ? (
            incoming.length === 0 ? (
              <p className="rounded-card bg-surface p-5 text-body text-ink-2">{en.warehouse.incomingNone}</p>
            ) : (
              incoming.map((listing) => <Incoming key={listing.id} listing={listing} onDone={() => setVersion((v) => v + 1)} />)
            )
          ) : (
            <div className="flex flex-col gap-3 rounded-card bg-surface p-5">
              <p className="text-small text-ink-2">{en.warehouse.adminOnly}</p>
              <ReceiveForm shipmentId={null} sentKg={null} onDone={() => {}} />
            </div>
          )}
        </section>
        <HandOver />
      </div>
    </div>
  );
}
