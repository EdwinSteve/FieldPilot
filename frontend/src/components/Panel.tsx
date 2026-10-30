import type { ReactNode } from "react";

interface PanelProps {
  title: string;
  children: ReactNode;
  error?: string | null;
  className?: string;
}

/** A titled section. A load or action error is shown at the top, never hidden. */
export function Panel({ title, children, error, className }: PanelProps) {
  return (
    <section className={`panel ${className ?? ""}`}>
      <h2>{title}</h2>
      {error ? (
        <p className="panel__error" role="alert">
          {error}
        </p>
      ) : null}
      {children}
    </section>
  );
}
