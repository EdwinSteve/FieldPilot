import { Icon, type IconName } from "./Icon";
import { IconCircle } from "./IconCircle";

interface StateViewProps {
  icon: IconName;
  title: string;
  detail?: string;
}

/** A whole screen with nothing to show yet: loading, an error or no data. */
export function StateView({ icon, title, detail }: StateViewProps) {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 px-6 text-center">
      <IconCircle tone="neutral" size="hero">
        <Icon name={icon} size={56} strokeWidth={1.8} />
      </IconCircle>
      <h1 className="text-head font-extrabold tracking-key">{title}</h1>
      {detail === undefined ? null : <p className="text-body leading-snug text-ink-2">{detail}</p>}
    </main>
  );
}
