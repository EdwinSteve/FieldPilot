import { useRef, useState } from "react";
import { api } from "../../api/endpoints";
import { useResource } from "../../hooks/useResource";
import type { FarmPlot, Lot } from "../api/lifecycle";
import type { Listing } from "../api/market";
import { BackLink } from "../components/BackHeader";
import { BigButton } from "../components/BigButton";
import { CropArt } from "../components/CropArt";
import { DoneBanner } from "../components/DoneBanner";
import { Icon, type IconName } from "../components/Icon";
import { DispatchSheet, JourneySheet, OfferSheet, SellSheet, WithdrawSheet } from "../components/SaleSheets";
import { StateView } from "../components/StateView";
import { useSales } from "../hooks/useSales";
import { en } from "../i18n/en";
import { formatCalendarDate } from "../lib/farmTime";
import { kgText } from "../lib/harvest";
import { cop, isOverdue, SALE_STEPS, saleStep } from "../lib/listing";
import { cropLabel } from "../lib/names";
import { plotToday } from "../lib/sowingDate";

const loadClock = () => api.clock();
const phoneNow = () => new Date().toISOString();

const STEP_ICONS: IconName[] = ["document", "arrowRight", "home", "bag"];

/** Where the sale is: a word and an icon for every step, never colour alone. */
function StepBar({ listing }: { listing: Listing }) {
  const current = saleStep(listing.status);
  return (
    // "Warehouse" is the longest word (80 px at 15 px): its column is wider, so it fits whole
    // down to a 320 px phone instead of being split as "Ware-house".
    <ol className="grid grid-cols-[1fr_1fr_1.6fr_1fr] gap-1" aria-label={en.sales.stepOf(current + 1, SALE_STEPS.length)}>
      {SALE_STEPS.map((step, i) => {
        const state = i < current ? "done" : i === current ? "now" : "todo";
        return (
          <li
            key={step}
            aria-current={state === "now" ? "step" : undefined}
            className={`flex min-w-0 flex-col items-center gap-1 rounded-tile px-0.5 py-2 text-center ${
              state === "now" ? "bg-tint text-primary-hover" : state === "done" ? "text-primary" : "text-ink-3"
            }`}
          >
            <Icon name={state === "done" ? "check" : STEP_ICONS[i]!} size={20} strokeWidth={2.4} />
            {/* Tight letters, never a split word: "Warehouse" fits a quarter of a phone. */}
            <span className={`text-caption leading-tight tracking-tight ${state === "now" ? "font-extrabold" : "font-semibold"}`}>
              {en.sales.steps[step]}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

/** What a listing did: the money and the kilos sold, side by side, each with its icon. */
function Results({ listing }: { listing: Listing }) {
  const total = listing.sold_kg + listing.stock_kg;
  const soldShare = total > 0 ? (listing.sold_kg / total) * 100 : 0;
  return (
    <div className="grid grid-cols-2 gap-2">
      <div className="flex flex-col gap-1 rounded-tile bg-tint px-3.5 py-3 text-primary-hover">
        <span className="flex items-center gap-1.5 text-caption font-bold">
          <Icon name="bag" size={16} strokeWidth={2.4} />
          {en.sales.earned}
        </span>
        <span className="text-row font-extrabold">{cop(listing.payouts_cop)}</span>
      </div>
      <div className="flex flex-col gap-1.5 rounded-tile bg-ground px-3.5 py-3">
        <span className="flex items-center gap-1.5 text-caption font-bold text-ink-2">
          <Icon name="check" size={16} strokeWidth={2.6} />
          {en.sales.sold}
        </span>
        <span className="text-body font-extrabold">{en.sales.soldOf(kgText(listing.sold_kg), kgText(total))}</span>
        <span className="flex h-1.5 overflow-hidden rounded-pill bg-divider" aria-hidden="true">
          <span className="rounded-pill bg-field" style={{ width: `${soldShare}%` }} />
        </span>
      </div>
    </div>
  );
}

type Sheet =
  | { kind: "sell"; lot: Lot }
  | { kind: "dispatch" | "withdraw" | "offer"; listing: Listing }
  | { kind: "journey"; lotCode: string };

function nextLine(listing: Listing): string {
  switch (listing.status) {
    case "awaiting_delivery":
      return en.sales.nextAwaiting(listing.warehouse.name);
    case "in_transit":
      return en.sales.nextTransit(listing.shipment?.id ?? 0);
    case "active":
      return en.sales.nextActive;
    case "sold_out":
      return en.sales.soldOut;
    case "withdrawn":
      return en.sales.withdrawn;
    case "expired":
      return en.sales.expired;
  }
}

function ListingCard({ listing, onSheet }: { listing: Listing; onSheet: (sheet: Sheet) => void }) {
  const overdue = isOverdue(listing);
  const shipment = listing.shipment;
  const lost = shipment?.received_kg == null ? 0 : shipment.dispatched_kg - shipment.received_kg;
  return (
    <article className="flex shrink-0 flex-col gap-3.5 rounded-card bg-surface p-4.5">
      <div className="flex items-center gap-3.5">
        <span className="flex size-16 shrink-0 items-center justify-center rounded-card bg-tint">
          <CropArt crop={listing.crop} size={48} />
        </span>
        <div className="flex min-w-0 flex-col gap-0.5">
          <h3 className="text-row font-extrabold">{cropLabel(listing.crop)}</h3>
          <span className="text-small text-ink-2">
            {en.sales.listingLine(kgText(listing.quantity_kg), cop(listing.farmer_price_per_kg_cop))}
          </span>
        </div>
      </div>
      <StepBar listing={listing} />
      {/* Past its day, "shoppers can buy it now" is no longer true: the red note below says what is. */}
      {overdue ? null : <p className="text-body leading-snug">{nextLine(listing)}</p>}
      {lost > 0 ? <p className="text-small text-ink-2">{en.sales.lostOnTheWay(kgText(lost))}</p> : null}
      {/* On the shelf, the best-before day is what moves the price (D086). */}
      {overdue && listing.best_before !== undefined ? (
        <p className="flex items-start gap-2 rounded-control bg-bad-tint px-3.5 py-3 text-small leading-snug font-bold text-bad-text">
          <Icon name="warning" size={18} strokeWidth={2.4} className="mt-0.5 shrink-0" />
          {en.sales.overdue(formatCalendarDate(listing.best_before))}
        </p>
      ) : null}
      {listing.status === "active" && !overdue && listing.best_before !== undefined ? (
        <p className="flex items-center gap-2 text-small font-bold text-ink-2">
          <Icon name="calendar" size={18} strokeWidth={2.4} />
          {en.sales.bestBefore(formatCalendarDate(listing.best_before), listing.days_left ?? null)}
        </p>
      ) : null}
      {listing.status === "active" && !overdue && listing.clearance != null ? (
        <p className="flex items-start gap-2 rounded-control bg-needs-tint px-3.5 py-3 text-small leading-snug font-bold text-needs-text">
          <Icon name="clock" size={18} strokeWidth={2.4} className="mt-0.5 shrink-0" />
          {en.sales.clearance(listing.clearance.discount_pct, formatCalendarDate(listing.clearance.ends_on))}
        </p>
      ) : null}
      <Results listing={listing} />
      <p className="flex items-center gap-2 text-small font-bold text-primary-hover">
        <Icon name="check" size={18} strokeWidth={2.6} />
        {en.sales.youKeep(String(listing.farmer_share_pct))} · {en.sales.shoppersPay(cop(listing.shelf_price_per_kg_cop))}
      </p>
      {listing.status === "awaiting_delivery" ? (
        <>
          <BigButton variant="primary" size="compact" onClick={() => onSheet({ kind: "dispatch", listing })}>
            <Icon name="arrowRight" size={24} strokeWidth={2.4} />
            {en.sales.dispatch}
          </BigButton>
          <BigButton variant="outline" size="compact" onClick={() => onSheet({ kind: "withdraw", listing })}>
            {en.sales.withdraw}
          </BigButton>
        </>
      ) : null}
      {listing.status === "active" ? (
        overdue ? null : (
          // A selling action, in the market's amber: not the same as opening the lot's journey.
          <button
            type="button"
            onClick={() => onSheet({ kind: "offer", listing })}
            className="press flex min-h-16 items-center justify-center gap-2.5 rounded-control border-2 border-needs bg-needs-tint text-row font-extrabold text-needs-text"
          >
            <Icon name="bag" size={22} strokeWidth={2.4} />
            {en.sales.offer}
          </button>
        )
      ) : null}
      {/* Details, not an action: a quiet row with the lot it opens. */}
      <button
        type="button"
        onClick={() => onSheet({ kind: "journey", lotCode: listing.lot_code })}
        className="press flex min-h-16 items-center gap-3 rounded-tile border-0 bg-ground px-3.5 py-2.5 text-left text-ink"
      >
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-surface text-primary">
          <Icon name="pin" size={20} strokeWidth={2.4} />
        </span>
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="text-body font-extrabold">{en.sales.journey}</span>
          <span className="truncate font-mono text-caption text-ink-3">{en.sales.lotLine(listing.lot_code)}</span>
        </span>
        <Icon name="forward" size={20} strokeWidth={2.6} className="shrink-0 text-ink-3" />
      </button>
    </article>
  );
}

function ReadyCard({ lot, onSell }: { lot: Lot; onSell: () => void }) {
  return (
    <article className="flex shrink-0 flex-col gap-3 rounded-card bg-surface p-4.5">
      <div className="flex items-center gap-3.5">
        <span className="flex size-16 shrink-0 items-center justify-center rounded-card bg-tint">
          <CropArt crop={lot.crop} size={48} />
        </span>
        <div className="flex min-w-0 flex-col gap-0.5">
          <h3 className="text-row font-extrabold">{cropLabel(lot.crop)}</h3>
          <span className="text-small text-ink-2">
            {en.sales.harvestRow(kgText(lot.quantity_kg), en.harvest.grades[lot.grade], formatCalendarDate(lot.harvested_on))}
          </span>
        </div>
      </div>
      <BigButton variant="primary" size="compact" onClick={onSell}>
        {en.sales.sell}
      </BigButton>
    </article>
  );
}

/** The farmer's harvests and their sales: sell, take to the warehouse, offer, see where it went. */
export function SalesScreen({ plot }: { plot: FarmPlot }) {
  const sales = useSales(plot.id);
  const clock = useResource(loadClock, 0);
  const [sheet, setSheet] = useState<Sheet | null>(null);
  /** What the last sale step did, said at the top until the farmer does the next thing. */
  const [said, setSaid] = useState<string | null>(null);
  const top = useRef<HTMLElement>(null);
  const open = (next: Sheet) => {
    setSaid(null);
    setSheet(next);
  };
  const today = plotToday(clock.data?.now ?? phoneNow(), plot.utc_offset_hours);
  const done = (text: string) => {
    setSheet(null);
    setSaid(text);
    sales.reload();
    top.current?.scrollTo({ top: 0, behavior: "smooth" });
  };
  return (
    <main ref={top} className="flex min-h-0 flex-1 flex-col gap-3.5 overflow-y-auto px-4.5 pt-5 pb-6">
      <header className="flex animate-screen-in items-center gap-3">
        <BackLink />
        <div className="flex flex-col">
          <h1 className="text-title font-extrabold tracking-title">{en.sales.title}</h1>
        </div>
      </header>
      <p className="px-0.5 text-lead leading-snug text-ink-2">{en.sales.lead}</p>
      {said === null ? null : <DoneBanner key={said} text={said} onClose={() => setSaid(null)} />}
      {sales.loading ? <StateView icon="hourglass" title={en.sales.loading} /> : null}
      {sales.failed ? (
        <StateView icon="warning" title={en.sales.loadFailed}>
          <div className="flex w-full max-w-80 flex-col pt-2">
            <BigButton variant="primary" onClick={sales.reload}>
              {en.sales.retry}
            </BigButton>
          </div>
        </StateView>
      ) : null}
      {!sales.loading && !sales.failed && sales.ready.length === 0 && sales.listings.length === 0 ? (
        <StateView icon="bag" title={en.sales.emptyTitle} detail={en.sales.emptyDetail} />
      ) : null}
      {sales.ready.length > 0 ? (
        <section className="flex flex-col gap-3">
          <h2 className="px-0.5 text-lead font-bold">{en.sales.readyTitle}</h2>
          {sales.ready.map((lot) => (
            <ReadyCard key={lot.code} lot={lot} onSell={() => open({ kind: "sell", lot })} />
          ))}
        </section>
      ) : null}
      {sales.listings.length > 0 ? (
        <section className="flex flex-col gap-3">
          <h2 className="px-0.5 text-lead font-bold">{en.sales.onSaleTitle}</h2>
          {sales.listings.map((listing) => (
            <ListingCard key={listing.id} listing={listing} onSheet={open} />
          ))}
        </section>
      ) : null}
      {sheet?.kind === "sell" ? <SellSheet lot={sheet.lot} onClose={() => setSheet(null)} onDone={done} /> : null}
      {sheet?.kind === "dispatch" ? <DispatchSheet listing={sheet.listing} onClose={() => setSheet(null)} onDone={done} /> : null}
      {sheet?.kind === "withdraw" ? <WithdrawSheet listing={sheet.listing} onClose={() => setSheet(null)} onDone={done} /> : null}
      {sheet?.kind === "offer" ? (
        <OfferSheet listing={sheet.listing} today={today} onClose={() => setSheet(null)} onDone={done} />
      ) : null}
      {sheet?.kind === "journey" ? <JourneySheet lotCode={sheet.lotCode} onClose={() => setSheet(null)} /> : null}
    </main>
  );
}
