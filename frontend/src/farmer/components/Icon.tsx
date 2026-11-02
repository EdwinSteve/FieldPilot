import type { ReactNode } from "react";

export const DROP_PATH = "M12 3c3 4 6 7.5 6 11a6 6 0 0 1-12 0c0-3.5 3-7 6-11z";
export const CLOUD_PATH = "M7 14a4 4 0 0 1 .5-8 5.5 5.5 0 0 1 10.5 2 3 3 0 0 1 0 6z";

const PATHS = {
  arrowDown: <path d="M12 5v14M6 13l6 6 6-6" />,
  arrowRight: <path d="M5 12h14M13 6l6 6-6 6" />,
  arrowUp: <path d="M12 19V5M6 11l6-6 6 6" />,
  back: <path d="M15 5l-7 7 7 7" />,
  bell: <path d="M6 8a6 6 0 0 1 12 0c0 7 3 8 3 8H3s3-1 3-8M10 20a2 2 0 0 0 4 0" />,
  calendar: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M3 10h18M8 3v4M16 3v4" />
    </>
  ),
  check: <path d="M5 12.5l4.5 4.5L19 7" />,
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  close: <path d="M6 6l12 12M18 6L6 18" />,
  cloud: <path d="M7 15a4 4 0 0 1 .5-8 5.5 5.5 0 0 1 10.5 2 3 3 0 0 1 0 6z" />,
  cloudOff: <path d="M7 15a4 4 0 0 1 .5-8 5.5 5.5 0 0 1 10.5 2 3 3 0 0 1 0 6zM5 21L19 5" />,
  cloudRain: <path d="M7 15a4 4 0 0 1 .5-8 5.5 5.5 0 0 1 10.5 2 3 3 0 0 1 0 6zM10 19l-1 2M15 19l-1 2" />,
  document: (
    <>
      <rect x="5" y="3" width="14" height="18" rx="2" />
      <path d="M9 8h6M9 12h6M9 16h3" />
    </>
  ),
  drop: <path d={DROP_PATH} />,
  dropRipple: (
    <>
      <path d={DROP_PATH} />
      <path d="M9 14.5a3 3 0 0 0 3 3" />
    </>
  ),
  forward: <path d="M9 5l7 7-7 7" />,
  home: <path d="M3 11l9-7 9 7v9H3z" />,
  hourglass: <path d="M6 3h12M6 21h12M7 3c0 5 5 6 5 9s-5 4-5 9M17 3c0 5-5 6-5 9s5 4 5 9" />,
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v6M12 7.5v.5" />
    </>
  ),
  lock: (
    <>
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </>
  ),
  mic: (
    <>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
    </>
  ),
  play: <path d="M7 4.5v15l12-7.5z" fill="currentColor" stroke="none" />,
  satellite: (
    <>
      <rect x="9" y="9" width="6" height="6" rx="1" />
      <path d="M3 5l6 4M21 5l-6 4M3 19l6-4M21 19l-6-4" />
    </>
  ),
  send: <path d="M12 19V5M6 11l6-6 6 6" />,
  sensor: (
    <>
      <path d="M12 3v12M8 7h8" />
      <circle cx="12" cy="18" r="3" />
    </>
  ),
  shield: (
    <>
      <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" />
      <path d="M8.5 12l2.5 2.5 4.5-5" />
    </>
  ),
  stopSquare: <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" stroke="none" />,
  undo: (
    <>
      <path d="M9 14L4 9l5-5" />
      <path d="M4 9h10a6 6 0 0 1 0 12h-3" />
    </>
  ),
  valve: <path d="M4 10h9a4 4 0 0 1 4 4v1M4 14h8M8 10V6M5 6h6" />,
  warning: <path d="M12 3l9 16H3zM12 10v4M12 17v.5" />,
  waterAdd: <path d="M3 18c3-1 4-4 9-4s6 3 9 4M12 3v8M9 8l3 3 3-3" />,
} satisfies Record<string, ReactNode>;

export type IconName = keyof typeof PATHS;

interface IconProps {
  name: IconName;
  size?: number;
  strokeWidth?: number;
  className?: string;
}

/** One stroke icon, in the current text colour. Always decorative: pair it with text. */
export function Icon({ name, size = 24, strokeWidth = 2.2, className }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      {PATHS[name]}
    </svg>
  );
}

interface StopSignProps {
  size: number;
  inverted?: boolean;
}

/** The octagon: red on light, white on the red banner. */
export function StopSign({ size, inverted = false }: StopSignProps) {
  const sign = inverted ? "var(--color-surface)" : "var(--color-stop)";
  const bar = inverted ? "var(--color-stop)" : "var(--color-surface)";
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M8 2h8l6 6v8l-6 6H8l-6-6V8z" fill={sign} />
      <rect x="7" y="10.5" width="10" height="3" rx="1" fill={bar} />
    </svg>
  );
}

/** A maize plant whose lower leaf has gone dry. */
export function PlantIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" strokeLinecap="round" aria-hidden="true">
      <path d="M12 21V11" stroke="var(--color-field)" strokeWidth="2" />
      <path d="M12 16c-4.5 0-6.5-2.5-6.5-6 4 0 6.5 2.2 6.5 6z" fill="var(--color-leaf-dry)" />
      <path d="M12 13c3.5 0 5.5-2.5 5.5-5.5-3.5 0-5.5 2.2-5.5 5.5z" fill="var(--color-leaf)" />
      <path d="M6 21h12" stroke="var(--color-earth)" strokeWidth="2" />
    </svg>
  );
}
