import { useContext, type ReactNode } from "react";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import { BackTarget } from "./backTarget";
import { Icon } from "./Icon";

/** Back to the screen the farmer came from, named for screen readers. */
export function BackLink() {
  const target = useContext(BackTarget);
  return (
    <a
      href={hrefOf(target)}
      aria-label={en.back[target.screen]}
      className="press flex size-13 shrink-0 items-center justify-center rounded-full bg-surface text-ink"
    >
      <Icon name="back" size={26} strokeWidth={2.5} />
    </a>
  );
}

export function BackHeader({ children }: { children: ReactNode }) {
  return (
    <header className="flex items-center gap-3 px-4.5 pt-5 pb-1.5">
      <BackLink />
      {children}
    </header>
  );
}
