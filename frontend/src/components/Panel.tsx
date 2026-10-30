import type { ReactNode } from "react";
import { type IconName, Icon } from "./icons";

interface PanelProps {
  title: string;
  children: ReactNode;
  error?: string | null;
  className?: string;
  icon?: IconName;
}

/** A titled section. A load or action error is shown at the top, never hidden. */
export function Panel({ title, children, error, className, icon }: PanelProps) {
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
      {children}
    </section>
  );
}
