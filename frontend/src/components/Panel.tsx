import type { ReactNode } from "react";
import { type IconName, Icon } from "./icons";

interface PanelProps {
  title: string;
  children: ReactNode;
  error?: string | null;
  className?: string;
  icon?: IconName;
  /** While true, a calm placeholder stands in for the content. */
  loading?: boolean;
}

/** A titled section. A load or action error is shown at the top, never hidden. */
export function Panel({ title, children, error, className, icon, loading }: PanelProps) {
  return (
    <section className={`panel ${className ?? ""}`}>
      <h2 className="panel__title">
        {icon ? <Icon name={icon} /> : null}
        {title}
      </h2>
      {error ? (
        <p className="panel__error" role="alert">
          {error}
        </p>
      ) : null}
      {loading ? (
        <div className="skeleton" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      ) : (
        children
      )}
    </section>
  );
}
