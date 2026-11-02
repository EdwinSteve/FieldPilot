import type { ReactNode } from "react";
import type { Level } from "../lib/statusLevel";
import { en } from "../i18n/en";
import type { TrendDirection } from "../lib/soilTrend";
import { Icon, type IconName } from "./Icon";
import { LEVEL_ICON, LEVEL_TILE } from "./levelStyle";

const TREND_ICONS: Record<TrendDirection, IconName> = {
  up: "arrowUp",
  down: "arrowDown",
  steady: "arrowRight",
};

interface StatusTileProps {
  href: string;
  level: Level;
  visual: ReactNode;
  value: string;
  /** Set smaller after the value, as in "20 of 32%". */
  valueNote?: string | null;
  label: string;
  /** An arrow beside the value: which way it is going, with no extra words to read. */
  trend?: TrendDirection | null;
}

/** The visual leads, the number confirms, the label names it. The arrow says it opens. */
export function StatusTile({
  href,
  level,
  visual,
  value,
  valueNote,
  label,
  trend = null,
}: StatusTileProps) {
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
        <span className="inline-flex items-center gap-0.5 text-key-lg font-extrabold">
          {value}
          {trend === null ? null : (
            <>
              <Icon name={TREND_ICONS[trend]} size={18} strokeWidth={3} />
              <span className="sr-only">{en.soil.trend[trend]}</span>
            </>
          )}
        </span>
        {valueNote ? <span className="text-caption font-bold">{valueNote}</span> : null}
      </span>
      <span className="text-caption font-bold">{label}</span>
    </a>
  );
}
