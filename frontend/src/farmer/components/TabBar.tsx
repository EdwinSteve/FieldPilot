import { en } from "../i18n/en";
import { hrefOf, type Tab } from "../lib/route";
import { Icon, type IconName } from "./Icon";

const TABS: { tab: Tab; icon: IconName; label: string }[] = [
  { tab: "today", icon: "home", label: en.tabs.today },
  { tab: "talk", icon: "mic", label: en.tabs.talk },
  { tab: "updates", icon: "bell", label: en.tabs.updates },
];

export function TabBar({ active }: { active: Tab }) {
  return (
    <nav
      aria-label={en.tabs.label}
      className="grid h-22 shrink-0 grid-cols-3 items-center border-t border-border bg-surface"
    >
      {TABS.map(({ tab, icon, label }) => {
        const current = tab === active;
        return (
          <a
            key={tab}
            href={hrefOf({ screen: tab })}
            aria-current={current ? "page" : undefined}
            className={`flex flex-col items-center gap-1 py-2 text-caption no-underline ${
              current ? "font-extrabold text-primary" : "font-semibold text-ink-3"
            }`}
          >
            <Icon name={icon} size={30} />
            {label}
          </a>
        );
      })}
    </nav>
  );
}
