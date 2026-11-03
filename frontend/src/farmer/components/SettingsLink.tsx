import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import { Icon } from "./Icon";

/** The way to Settings, top right: a big gear with its name under it, no box, so Stop stays the strong one. */
export function SettingsLink() {
  return (
    <a
      href={hrefOf({ screen: "settings" })}
      className="group press flex min-h-16 min-w-16 shrink-0 flex-col items-center justify-center gap-0.5 rounded-control px-1 text-caption font-extrabold text-ink-2 no-underline"
    >
      <Icon
        name="gear"
        size={32}
        strokeWidth={2}
        className="transition-transform duration-300 ease-calm group-hover:rotate-45 group-active:rotate-90"
      />
      {en.settings.open}
    </a>
  );
}
