import type { ReactNode } from "react";

interface InfoRowProps {
  icon: ReactNode;
  children: ReactNode;
  /** The figure on the right; left out on rows that are only a sentence. */
  value?: ReactNode;
}

/** One line of a list card. Divides itself from the next row. */
export function InfoRow({ icon, children, value }: InfoRowProps) {
  return (
    <div className="flex items-center gap-3.5 border-b border-divider py-3.5 last:border-b-0">
      {icon}
      <span className="flex-1 text-body font-semibold">{children}</span>
      {value}
    </div>
  );
}
