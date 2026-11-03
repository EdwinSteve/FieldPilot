import { useSales } from "../hooks/useSales";
import { en } from "../i18n/en";
import { cop } from "../lib/listing";
import { hrefOf } from "../lib/route";
import { Icon } from "./Icon";

/** "Your sales" on Today and What to plant: what is ready to sell, what is on sale, what it earned. */
export function SalesCard({ plotId }: { plotId: number }) {
  const sales = useSales(plotId);
  const earned = sales.listings.reduce((sum, listing) => sum + listing.payouts_cop, 0);
  const parts = [
    sales.ready.length > 0 ? en.sales.card.ready(sales.ready.length) : null,
    sales.listings.length > 0 ? en.sales.card.onSale(sales.listings.length) : null,
    earned > 0 ? en.sales.card.earned(cop(earned)) : null,
  ].filter((part) => part !== null);
  // Always there, so selling is never hidden: the summary once it loads, an invitation until then.
  // A failed read says why on the sales screen, not by the card vanishing.
  if (parts.length === 0) parts.push(en.sales.card.none);
  return (
    <a
      href={hrefOf({ screen: "sales" })}
      className="press flex min-h-16 shrink-0 animate-card-in items-center gap-3.5 rounded-card bg-surface px-4.5 py-3.5 text-ink no-underline"
    >
      <span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-tint text-primary">
        <Icon name="bag" size={26} />
      </span>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="text-lead font-extrabold">{en.sales.card.title}</span>
        <span className="text-small text-ink-2">{parts.join(" · ")}</span>
      </span>
      <Icon name="forward" size={22} className="shrink-0 text-ink-3" />
    </a>
  );
}
