import type { ReactNode } from "react";
import type { Level } from "../lib/statusLevel";
import { Icon } from "./Icon";
import { LEVEL_ICON, LEVEL_TILE } from "./levelStyle";

interface StatusTileProps {
  href: string;
  level: Level;
  visual: ReactNode;
  value: string;
  /** Set smaller after the value, as in "20 of 32%". */
  valueNote?: string | null;
  label: string;
}

/** The visual leads, the number confirms, the label names it. The arrow says it opens. */
export function StatusTile({ href, level, visual, value, valueNote, label }: StatusTileProps) {
  const levelIcon = LEVEL_ICON[level];
  return (
    <a
      href={href}
      className={`press relative flex flex-col items-center gap-1 rounded-tile px-1 py-3 no-underline ${LEVEL_TILE[level]}`}
    >
      {levelIcon === null ? null : (
        <Icon name={levelIcon} size={16} strokeWidth={2.6} className="absolute top-2 left-2" />
      )}
      <Icon name="forward" size={16} strokeWidth={2.6} className="absolute top-2 right-2" />
      {visual}
      <span className="flex flex-wrap items-baseline justify-center gap-x-1">
        <span className="text-key-lg font-extrabold">{value}</span>
        {valueNote ? <span className="text-caption font-bold">{valueNote}</span> : null}
      </span>
      <span className="text-caption font-bold">{label}</span>
    </a>
  );
}
