import { en } from "../i18n/en";
import { hrefOf, type Tab } from "../lib/route";
import { Icon, type IconName } from "./Icon";

/** A chat bubble for Talk: the sign farmers know from messaging apps. */
const TABS: { tab: Tab; icon: IconName; label: string }[] = [
  { tab: "today", icon: "home", label: en.tabs.today },
  { tab: "talk", icon: "chat", label: en.tabs.talk },
  { tab: "updates", icon: "bell", label: en.tabs.updates },
];

/** More than this shows as "9+": the badge says there is news, not how much. */
const MAX_COUNT = 9;

interface TabBarProps {
  active: Tab;
  /** Unread updates, counted on the Updates tab. */
  unread: number;
  /** A decision waits: Today shows a dot while the farmer is elsewhere. */
  decisionWaiting: boolean;
}

type Mark = { kind: "count"; text: string; spoken: string } | { kind: "dot"; spoken: string } | null;

function markOf(tab: Tab, current: boolean, { unread, decisionWaiting }: TabBarProps): Mark {
  if (tab === "updates" && unread > 0) {
    const text = unread > MAX_COUNT ? `${MAX_COUNT}+` : String(unread);
    return { kind: "count", text, spoken: en.tabs.unread(unread) };
  }
  if (tab === "today" && decisionWaiting && !current) {
    return { kind: "dot", spoken: en.tabs.decisionWaiting };
  }
  return null;
}

function Badge({ mark }: { mark: Mark }) {
  if (mark === null) return null;
  if (mark.kind === "dot") {
    return (
      <span
        aria-hidden="true"
        className="absolute -top-0.5 left-5.5 size-4 rounded-full border-2 border-surface bg-needs"
      />
    );
  }
  return (
    <span
      aria-hidden="true"
      className="absolute -top-1.5 left-5 flex h-6 min-w-6 items-center justify-center rounded-pill border-2 border-surface bg-stop px-1 text-caption leading-none font-extrabold text-surface"
    >
      {mark.text}
    </span>
  );
}

export function TabBar(props: TabBarProps) {
  return (
    <nav
      aria-label={en.tabs.label}
      className="grid h-[calc(5.5rem+env(safe-area-inset-bottom))] shrink-0 grid-cols-3 items-center border-t border-border bg-surface pb-[env(safe-area-inset-bottom)]"
    >
      {TABS.map(({ tab, icon, label }) => {
        const current = tab === props.active;
        const mark = markOf(tab, current, props);
        return (
          <a
            key={tab}
            href={hrefOf({ screen: tab })}
            aria-current={current ? "page" : undefined}
            className={`press flex flex-col items-center gap-1 py-2 text-caption no-underline ${
              current ? "font-extrabold text-primary" : "font-semibold text-ink-3"
            }`}
          >
            <span className="relative">
              <Icon name={icon} size={30} />
              <Badge mark={mark} />
            </span>
            {label}
            {mark === null ? null : <span className="sr-only">, {mark.spoken}</span>}
          </a>
        );
      })}
    </nav>
  );
}
