// The sheets of selling: put a harvest on sale, take it to the warehouse, take it off sale,
// start an offer, and see where the harvest went. Each says what happens before the farmer taps.
import { useState } from "react";
import { useResource } from "../../hooks/useResource";
import type { Lot } from "../api/lifecycle";
import { market, type Listing, type Passport, type Warehouse } from "../api/market";
import { en } from "../i18n/en";
import { formatCalendarDate } from "../lib/farmTime";
import { kgText } from "../lib/harvest";
import {
  cop,
  FEES,
  farmerShare,
  listingProblems,
  lowestPrice,
  offerProblem,
  plusDaysIso,
  shelfPrice,
  typedWhole,
} from "../lib/listing";
import { marketFailure, type MarketFailure } from "../lib/marketFailure";
import { cropLabel } from "../lib/names";
import { BigButton } from "./BigButton";
import { Choices } from "./Choices";
import { Icon } from "./Icon";
import { Sheet } from "./Sheet";
import { TextField } from "./TextField";

function Failure({ failure }: { failure: MarketFailure | null }) {
  if (failure === null) return null;
  return (
    <p role="alert" className="rounded-control bg-needs-tint px-4 py-3 text-small font-bold text-needs-text">
      {en.sales.failures[failure]}
    </p>
  );
}

/** Runs one market step: busy while it goes, the failure in words when it does not. */
function useStep() {
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<MarketFailure | null>(null);
  const run = async (step: () => Promise<unknown>, done: () => void) => {
    setBusy(true);
    setFailure(null);
    try {
      await step();
      done();
    } catch (caught) {
      setFailure(marketFailure(caught, navigator.onLine));
    } finally {
      setBusy(false);
    }
  };
  return { busy, failure, run };
}

/** The price as shoppers will see it, and the share the farmer keeps: live, as the farmer types. */
function PricePreview({ price, discount = 0 }: { price: number; discount?: number }) {
  if (!(price > 0)) return null;
  const share = farmerShare(price, discount);
  const fair = price >= lowestPrice(discount);
  return (
    <div
      aria-live="polite"
      className={`flex flex-col gap-1 rounded-control px-4 py-3 ${fair ? "bg-tint text-primary-hover" : "bg-needs-tint text-needs-text"}`}
    >
      <span className="text-small font-bold">{en.sales.form.preview}</span>
      <span className="text-row font-extrabold">{en.sales.shoppersPay(cop(shelfPrice(price, discount)))}</span>
      <span className="flex items-center gap-2 text-body font-extrabold">
        <Icon name={fair ? "check" : "warning"} size={20} strokeWidth={2.6} />
        {en.sales.youKeep(String(share))}
      </span>
    </div>
  );
}

const loadWarehouses = () => market.warehouses();

export function SellSheet({ lot, onClose, onDone }: { lot: Lot; onClose: () => void; onDone: () => void }) {
  const warehouses = useResource(loadWarehouses, 0).data ?? [];
  const [price, setPrice] = useState("");
  const [kg, setKg] = useState(String(Math.floor(lot.quantity_kg)));
  const [warehouseId, setWarehouseId] = useState<number | null>(null);
  const [tried, setTried] = useState(false);
  const step = useStep();
  const problems = listingProblems({ price, kg }, lot.quantity_kg);
  const chosen: Warehouse | undefined = warehouses.find((w) => w.id === warehouseId) ?? warehouses[0];
  const name = cropLabel(lot.crop);

  const submit = () => {
    setTried(true);
    if (problems.price !== null || problems.kg !== null || chosen === undefined) return;
    void step.run(
      () => market.list(lot.code, { farmer_price_per_kg_cop: Number(price), quantity_kg: Number(kg), warehouse_id: chosen.id }),
      onDone,
    );
  };

  return (
    <Sheet label={en.sales.form.title(name)} onClose={onClose}>
      <h2 className="text-head font-extrabold tracking-key">{en.sales.form.title(name)}</h2>
      <p className="text-body text-ink-2">{en.sales.form.harvested(kgText(lot.quantity_kg), en.harvest.grades[lot.grade])}</p>
      <TextField
        label={en.sales.form.price}
        hint={en.sales.form.priceHint(cop(lowestPrice()))}
        prefix="COP"
        value={price}
        onChange={(value) => setPrice(typedWhole(value))}
        problem={tried && problems.price !== null ? en.sales.form.problems.price[problems.price] : null}
        inputMode="numeric"
        autoComplete="off"
      />
      <PricePreview price={Number(price)} />
      <p className="px-0.5 text-small text-ink-3">
        {en.sales.form.fees(cop(FEES.logisticsPerKg), FEES.platformPct)}
      </p>
      <TextField
        label={en.sales.form.kg}
        hint={en.sales.form.kgHint(kgText(lot.quantity_kg))}
        value={kg}
        onChange={(value) => setKg(typedWhole(value))}
        problem={tried && problems.kg !== null ? en.sales.form.problems.kg[problems.kg] : null}
        inputMode="numeric"
        autoComplete="off"
      />
      {warehouses.length > 1 ? (
        <fieldset className="flex flex-col gap-2 border-0 p-0">
          <legend className="px-0.5 pb-2 text-body font-bold text-ink-2">{en.sales.form.warehouse}</legend>
          <Choices
            options={warehouses.map((w) => w.id)}
            chosen={chosen?.id ?? null}
            label={(id) => warehouses.find((w) => w.id === id)?.name ?? ""}
            onChoose={setWarehouseId}
          />
        </fieldset>
      ) : chosen === undefined ? null : (
        <div className="flex gap-3 rounded-control bg-ground px-4 py-3">
          <Icon name="home" size={24} className="mt-0.5 shrink-0 text-primary" />
          <div className="flex flex-col">
            <span className="text-small font-bold text-ink-3">{en.sales.form.warehouse}</span>
            <span className="text-body font-bold">{chosen.name}</span>
            <span className="text-small text-ink-2">
              {chosen.municipality}
              {chosen.cold_storage ? ` · ${en.sales.form.cold}` : ""}
            </span>
          </div>
        </div>
      )}
      <Failure failure={step.failure} />
      <BigButton variant="primary" disabled={step.busy} onClick={submit}>
        {step.busy ? en.sales.form.submitting : en.sales.form.submit}
      </BigButton>
      <BigButton variant="outline" size="compact" onClick={onClose}>
        {en.sales.form.cancel}
      </BigButton>
    </Sheet>
  );
}

/** A yes-or-cancel sheet for a step that changes the sale. */
function ConfirmSheet({
  title,
  detail,
  after,
  confirm,
  busyLabel,
  step,
  onConfirm,
  onClose,
}: {
  title: string;
  detail: string;
  after?: string;
  confirm: string;
  busyLabel: string;
  step: ReturnType<typeof useStep>;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Sheet label={title} onClose={onClose}>
      <h2 className="text-head font-extrabold tracking-key">{title}</h2>
      <p className="text-body leading-snug">{detail}</p>
      {after === undefined ? null : <p className="text-body leading-snug text-ink-2">{after}</p>}
      <Failure failure={step.failure} />
      <BigButton variant="primary" disabled={step.busy} onClick={onConfirm}>
        {step.busy ? busyLabel : confirm}
      </BigButton>
      <BigButton variant="outline" size="compact" onClick={onClose}>
        {en.sales.form.cancel}
      </BigButton>
    </Sheet>
  );
}

export function DispatchSheet({ listing, onClose, onDone }: { listing: Listing; onClose: () => void; onDone: () => void }) {
  const step = useStep();
  const words = en.sales.dispatchSheet;
  return (
    <ConfirmSheet
      title={words.title}
      detail={words.detail(kgText(listing.quantity_kg), listing.warehouse.name, listing.warehouse.municipality)}
      after={words.after}
      confirm={words.confirm}
      busyLabel={words.busy}
      step={step}
      onConfirm={() => void step.run(() => market.dispatch(listing.id), onDone)}
      onClose={onClose}
    />
  );
}

export function WithdrawSheet({ listing, onClose, onDone }: { listing: Listing; onClose: () => void; onDone: () => void }) {
  const step = useStep();
  const words = en.sales.withdrawSheet;
  return (
    <ConfirmSheet
      title={words.title}
      detail={words.detail}
      confirm={words.confirm}
      busyLabel={words.busy}
      step={step}
      onConfirm={() => void step.run(() => market.withdraw(listing.id), onDone)}
      onClose={onClose}
    />
  );
}

const DISCOUNTS = [5, 10, 15, 20, 25, 30] as const;
const DAYS = [1, 3, 7] as const;

export function OfferSheet({
  listing,
  today,
  onClose,
  onDone,
}: {
  listing: Listing;
  /** The plot's today: the offer starts on it. */
  today: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const [discount, setDiscount] = useState<number | null>(null);
  const [days, setDays] = useState<number>(3);
  const [tried, setTried] = useState(false);
  const step = useStep();
  const words = en.sales.offerSheet;
  const price = listing.farmer_price_per_kg_cop;
  const problem = offerProblem(discount === null ? "" : String(discount), price);
  const submit = () => {
    setTried(true);
    if (problem !== null || discount === null) return;
    void step.run(
      () => market.offer(listing.id, { discount_pct: discount, starts_on: today, ends_on: plusDaysIso(today, days - 1) }),
      onDone,
    );
  };
  return (
    <Sheet label={words.title} onClose={onClose}>
      <h2 className="text-head font-extrabold tracking-key">{words.title}</h2>
      <p className="text-body text-ink-2">{words.lead}</p>
      <fieldset className="flex flex-col gap-2 border-0 p-0">
        <legend className="px-0.5 pb-2 text-body font-bold text-ink-2">{words.discount}</legend>
        <Choices
          options={DISCOUNTS}
          chosen={discount}
          label={(pct) => `${pct}%`}
          onChoose={setDiscount}
        />
      </fieldset>
      {discount === null ? null : (
        <p
          aria-live="polite"
          className={`rounded-control px-4 py-3 text-body font-extrabold ${
            problem === null ? "bg-tint text-primary-hover" : "bg-needs-tint text-needs-text"
          }`}
        >
          {words.preview(cop(shelfPrice(price, discount)), String(farmerShare(price, discount)))}
        </p>
      )}
      {tried && problem !== null ? (
        <p className="flex items-center gap-2 px-0.5 text-small font-bold text-bad-text">
          <Icon name="warning" size={18} strokeWidth={2.4} className="shrink-0" />
          {words.problems[problem]}
        </p>
      ) : null}
      <fieldset className="flex flex-col gap-2 border-0 p-0">
        <legend className="px-0.5 pb-2 text-body font-bold text-ink-2">{words.days}</legend>
        <Choices options={DAYS} chosen={days} label={(d) => words.dayCount(d)} onChoose={setDays} />
      </fieldset>
      <Failure failure={step.failure} />
      <BigButton variant="primary" disabled={step.busy} onClick={submit}>
        {step.busy ? words.busy : words.confirm}
      </BigButton>
      <BigButton variant="outline" size="compact" onClick={onClose}>
        {en.sales.form.cancel}
      </BigButton>
    </Sheet>
  );
}

const STEP_ICON = {
  commissioning: "check",
  shipping: "arrowRight",
  receiving: "home",
  retail_selling: "bag",
} as const;

/** The lot's path, from the passport: harvested, taken, received, each sale. */
export function JourneySheet({ lotCode, onClose }: { lotCode: string; onClose: () => void }) {
  const [load] = useState(() => () => market.passport(lotCode));
  const passport = useResource<Passport>(load, 0);
  const words = en.sales.journeySheet;
  return (
    <Sheet label={words.title} onClose={onClose}>
      <h2 className="text-head font-extrabold tracking-key">{words.title}</h2>
      {passport.data === null ? (
        <p className="text-body text-ink-2">{passport.error === null ? words.loading : words.failed}</p>
      ) : (
        <>
          <p
            className={`flex items-center gap-2 rounded-control px-4 py-3 text-body font-bold ${
              passport.data.integrity.verified ? "bg-tint text-primary-hover" : "bg-bad-tint text-bad-text"
            }`}
          >
            <Icon name={passport.data.integrity.verified ? "shield" : "warning"} size={22} className="shrink-0" />
            {passport.data.integrity.verified ? words.verified : words.broken}
          </p>
          <ol className="flex flex-col">
            {passport.data.journey.map((step, i) => (
              <li key={i} className="flex gap-3.5">
                <div className="flex flex-col items-center">
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-tint text-primary">
                    <Icon name={STEP_ICON[step.step]} size={20} strokeWidth={2.4} />
                  </span>
                  {i < passport.data!.journey.length - 1 ? <span className="w-0.5 flex-1 bg-border" /> : null}
                </div>
                <div className="flex flex-col pb-4">
                  <span className="text-body font-extrabold">{words.steps[step.step]}</span>
                  <span className="text-small text-ink-2">
                    {formatCalendarDate(step.on)} · {words.kg(kgText(step.quantity_kg))}
                    {step.place === null ? "" : ` · ${step.place}`}
                  </span>
                </div>
              </li>
            ))}
          </ol>
        </>
      )}
      <BigButton variant="outline" size="compact" onClick={onClose}>
        {words.close}
      </BigButton>
    </Sheet>
  );
}
