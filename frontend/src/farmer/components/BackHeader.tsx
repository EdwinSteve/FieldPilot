import type { ReactNode } from "react";
import { Icon } from "./Icon";

interface BackLinkProps {
  href: string;
  label: string;
}

export function BackLink({ href, label }: BackLinkProps) {
  return (
    <a
      href={href}
      aria-label={label}
      className="press flex size-13 shrink-0 items-center justify-center rounded-full bg-surface text-ink"
    >
      <Icon name="back" size={26} strokeWidth={2.5} />
    </a>
  );
}

interface BackHeaderProps extends BackLinkProps {
  children: ReactNode;
}

export function BackHeader({ href, label, children }: BackHeaderProps) {
  return (
    <header className="flex items-center gap-3 px-4.5 pt-5 pb-1.5">
      <BackLink href={href} label={label} />
      {children}
    </header>
  );
}
