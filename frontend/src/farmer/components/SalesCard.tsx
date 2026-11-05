import { useSales, type Sales } from "../hooks/useSales";
import { en } from "../i18n/en";
import { cop } from "../lib/listing";
import { hrefOf } from "../lib/route";
import { Icon } from "./Icon";

/** "Your sales" on Today and What to plant: what is ready to sell, what is on sale, what it earned. */
export function SalesCard({ plotId }: { plotId: number }) {
  return <SalesSummary sales={useSales(plotId)} />;
}

/** The card itself, for a screen that already reads the sales (Today places it by them). */
export function SalesSummary({ sales }: { sales: Sales }) {
  const earned = sales.listings.reduce((sum, listing) => sum + listing.payouts_cop, 0);
  // Each chip in the colour of what it says: a harvest to sell asks for the farmer (amber),
  // what is on sale is news (blue), money earned is good (green). The words carry it too.
  const parts = [
    sales.ready.length > 0 ? { text: en.sales.card.ready(sales.ready.length), tone: "bg-needs-tint text-needs-text" } : null,
    sales.listings.length > 0 ? { text: en.sales.card.onSale(sales.listings.length), tone: "bg-undo-tint text-undo-text" } : null,
    earned > 0 ? { text: en.sales.card.earned(cop(earned)), tone: "bg-tint text-primary-hover" } : null,
  ].filter((part) => part !== null);
  // Always there, so selling is never hidden: the summary once it loads, an invitation until then.
  // A failed read says why on the sales screen, not by the card vanishing.
  const invite = parts.length === 0;
  return (
    <a
      href={hrefOf({ screen: "sales" })}
      className="press flex min-h-16 shrink-0 animate-card-in items-center gap-3.5 rounded-card bg-surface px-4.5 py-3.5 text-ink no-underline"
    >
      {/* The market's amber, not the farm's green: selling is its own thing. */}
      <span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-needs-tint text-needs-icon">
        <Icon name="bag" size={26} />
      </span>
      <span className="flex min-w-0 flex-1 flex-col gap-1.5">
        <span className="text-lead font-extrabold">{en.sales.card.title}</span>
        {/* The numbers as chips; with nothing to count yet, an invitation in plain words. */}
        {invite ? (
          <span className="text-small text-ink-2">{en.sales.card.none}</span>
        ) : (
          <span className="flex flex-wrap gap-1.5">
            {parts.map((part) => (
              <span key={part.text} className={`rounded-pill px-2.5 py-1 text-caption font-bold ${part.tone}`}>
                {part.text}
              </span>
            ))}
          </span>
        )}
      </span>
      <Icon name="forward" size={22} className="shrink-0 text-ink-3" />
    </a>
  );
}
