import type { ReactNode } from "react";

export type ChipTone = "needs" | "undo" | "good" | "neutral";

const TONES: Record<ChipTone, string> = {
  needs: "bg-needs-tint text-needs-text",
  undo: "bg-undo-tint text-undo-text",
  good: "bg-tint text-primary-hover",
  neutral: "bg-divider text-ink-2",
};

interface ChipProps {
  tone: ChipTone;
  children: ReactNode;
}

export function Chip({ tone, children }: ChipProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-pill px-3 py-1.5 text-caption font-extrabold ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}
