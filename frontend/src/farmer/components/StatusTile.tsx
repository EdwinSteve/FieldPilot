import type { ReactNode } from "react";

type TileTone = "needs" | "rain" | "good";

const TONES: Record<TileTone, string> = {
  needs: "bg-needs-tint text-needs-text",
  rain: "bg-undo-tint text-undo-text",
  good: "bg-tint text-primary-hover",
};

interface StatusTileProps {
  href: string;
  tone: TileTone;
  visual: ReactNode;
  value: string;
  label: string;
}

/** The visual leads, the number confirms, the label names it. */
export function StatusTile({ href, tone, visual, value, label }: StatusTileProps) {
  return (
    <a
      href={href}
      className={`flex flex-col items-center gap-1 rounded-tile px-1 py-3 no-underline ${TONES[tone]}`}
    >
      {visual}
      <span className="text-key-lg font-extrabold">{value}</span>
      <span className="text-caption font-bold">{label}</span>
    </a>
  );
}
