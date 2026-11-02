import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import type { UpdateItem } from "../view-models/types";
import { Icon } from "./Icon";
import { UpdateRow } from "./UpdateRow";

/** The newest few updates on Today, with the way to all of them. */
export function RecentUpdates({ items }: { items: UpdateItem[] }) {
  return (
    <section className="flex flex-col gap-2.5">
      <div className="flex min-h-8 items-center justify-between px-0.5">
        <h2 className="text-lead font-bold">{en.today.recentUpdates}</h2>
        <a
          href={hrefOf({ screen: "updates" })}
          className="press inline-flex min-h-12 items-center gap-1 text-small font-bold text-primary no-underline"
        >
          {en.today.seeAll}
          <Icon name="forward" size={18} strokeWidth={2.6} />
        </a>
      </div>
      {items.map((item) => (
        <UpdateRow key={item.id} item={item} />
      ))}
      {items.length === 0 ? (
        <p className="rounded-tile bg-surface p-4 text-body text-ink-2">{en.updates.empty}</p>
      ) : null}
    </section>
  );
}
