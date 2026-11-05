import type { ReactNode } from "react";
import { PlantIcon } from "./Icon";

// Flat pictures of the planner's crops (docs/api.md §9), in the app's own colours,
// so a farmer recognises the crop before reading its name. Decorative: the name says it.

const LEAF = "var(--color-field)";
const LEAF_LIGHT = "var(--color-leaf)";
const DRY = "var(--color-leaf-dry)";
const EARTH = "var(--color-earth)";
const GRAIN = "var(--color-ring)";
const OUTLINE = "var(--color-ink-3)";

const ART: Record<string, ReactNode> = {
  maize: (
    <>
      <path d="M24 44c-2-8-2-18 0-30" stroke={LEAF} strokeWidth="3" strokeLinecap="round" fill="none" />
      <ellipse cx="24" cy="21" rx="7" ry="14" fill={GRAIN} />
      <path d="M20 12v20M24 8v26M28 12v20" stroke={EARTH} strokeWidth="1.2" opacity="0.5" />
      <path d="M24 40c-9-3-13-12-12-22 5 6 8 13 12 22z" fill={LEAF} />
      <path d="M24 40c9-3 13-12 12-22-5 6-8 13-12 22z" fill={LEAF_LIGHT} />
    </>
  ),
  common_bean: (
    <>
      <path d="M10 14c10 0 26 6 28 22-2 4-6 4-9 1-4-10-12-14-21-15-3-3-2-7 2-8z" fill={LEAF_LIGHT} />
      <circle cx="16" cy="19" r="3" fill={LEAF} />
      <circle cx="23" cy="23" r="3" fill={LEAF} />
      <circle cx="29" cy="29" r="3" fill={LEAF} />
      <ellipse cx="14" cy="38" rx="5" ry="3.5" fill="var(--color-stop)" />
      <ellipse cx="25" cy="42" rx="5" ry="3.5" fill={EARTH} />
    </>
  ),
  sorghum: (
    <>
      <path d="M24 46V22" stroke={LEAF} strokeWidth="3" strokeLinecap="round" />
      <path d="M24 36c-6-1-11-5-12-11 6 1 10 5 12 11zM24 32c6-1 11-5 12-11-6 1-10 5-12 11z" fill={LEAF_LIGHT} />
      {[
        [24, 6], [20, 10], [28, 10], [24, 12], [18, 15], [30, 15], [22, 17], [26, 17], [24, 21],
      ].map(([x, y]) => (
        <circle key={`${x}-${y}`} cx={x} cy={y} r="3.4" fill={EARTH} />
      ))}
    </>
  ),
  soybean: (
    <>
      <path d="M14 8c-4 10-4 22 2 32 3 2 7 1 8-2-4-9-4-20 0-28-2-4-7-5-10-2z" fill={DRY} />
      <circle cx="17" cy="16" r="3" fill={GRAIN} />
      <circle cx="17" cy="25" r="3" fill={GRAIN} />
      <circle cx="19" cy="33" r="3" fill={GRAIN} />
      <path d="M28 40c0-10 4-18 12-22 1 10-4 18-12 22z" fill={LEAF} />
      <path d="M28 40c-1-6 1-12 5-16" stroke={LEAF_LIGHT} strokeWidth="1.5" fill="none" />
    </>
  ),
  groundnut: (
    <>
      <path
        d="M17 8c6 0 9 5 8 10-1 3 1 5 4 6 6 2 9 7 7 13-2 6-9 8-14 4-3-2-5-4-8-6-5-3-7-9-5-15 1-6 4-12 8-12z"
        fill={DRY}
        stroke={EARTH}
        strokeWidth="1.5"
      />
      <path d="M14 16l3 2M12 24l3 1M24 32l3 1M28 38l2-2" stroke={EARTH} strokeWidth="1.5" strokeLinecap="round" />
    </>
  ),
  cotton: (
    <>
      <path d="M24 46V30" stroke={EARTH} strokeWidth="3" strokeLinecap="round" />
      <path d="M14 30c4 4 16 4 20 0l-3 6c-4 2-10 2-14 0z" fill={EARTH} />
      {[
        [17, 22], [31, 22], [24, 17], [20, 28], [28, 28], [24, 24],
      ].map(([x, y]) => (
        <circle key={`${x}-${y}`} cx={x} cy={y} r="7" fill="var(--color-surface)" stroke={OUTLINE} strokeWidth="1.2" />
      ))}
    </>
  ),
  tomato: (
    <>
      <circle cx="24" cy="28" r="15" fill="var(--color-stop)" />
      <ellipse cx="18" cy="23" rx="4" ry="2.5" fill="var(--color-surface)" opacity="0.35" />
      <path d="M24 14l3 4 5-2-3 5 5 2-6 1-4 3-4-3-6-1 5-2-3-5 5 2z" fill={LEAF} />
      <path d="M24 14V7" stroke={LEAF} strokeWidth="2.5" strokeLinecap="round" />
    </>
  ),
  potato: (
    <>
      <path d="M8 26c0-10 9-16 19-15s15 8 13 17-11 13-20 12S8 34 8 26z" fill={EARTH} />
      <path d="M14 22c1-1 2-1 2 0M24 18c1-1 2-1 2 0M30 28c1-1 2-1 2 0M19 32c1-1 2-1 2 0" stroke="var(--color-ink-2)" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M33 13c2-5 6-6 8-4-1 3-4 5-8 4z" fill={LEAF_LIGHT} />
    </>
  ),
};

/** The crop's picture, or the app's plant for a crop without one yet. */
export function CropArt({ crop, size }: { crop: string; size: number }) {
  const art = ART[crop];
  if (art === undefined) return <PlantIcon size={size} />;
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-hidden="true">
      {art}
    </svg>
  );
}
