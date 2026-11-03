import type { ReactNode } from "react";

export const DROP_PATH = "M12 3c3 4 6 7.5 6 11a6 6 0 0 1-12 0c0-3.5 3-7 6-11z";
export const CLOUD_PATH = "M7 14a4 4 0 0 1 .5-8 5.5 5.5 0 0 1 10.5 2 3 3 0 0 1 0 6z";

const PATHS = {
  arrowDown: <path d="M12 5v14M6 13l6 6 6-6" />,
  bag: <path d="M9 3h6l-1.5 3h-3zM10.5 6C6 8 4 12 4 15a6 6 0 0 0 6 6h4a6 6 0 0 0 6-6c0-3-2-7-6.5-9z" />,
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
  chat: (
    <path d="M5 4h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-8l-5 4v-4H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z" />
  ),
  call: (
    <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z" />
  ),
  check: <path d="M5 12.5l4.5 4.5L19 7" />,
  chevronDown: <path d="M6 9l6 6 6-6" />,
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
  eye: (
    <>
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  eyeOff: (
    <>
      <path d="M10.6 5.1A9.8 9.8 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-2.6 3.6M6.6 6.6A17 17 0 0 0 2 12s3.5 7 10 7a9.6 9.6 0 0 0 5.4-1.6" />
      <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2M3 3l18 18" />
    </>
  ),
  field: <path d="M4 7l8-3 8 3v10l-8 3-8-3zM4 12l8 3 8-3" />,
  forward: <path d="M9 5l7 7-7 7" />,
  gear: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2.5v2.5M12 19v2.5M21.5 12H19M5 12H2.5M18.7 5.3l-1.8 1.8M7.1 16.9l-1.8 1.8M18.7 18.7l-1.8-1.8M7.1 7.1L5.3 5.3" />
      <circle cx="12" cy="12" r="7" />
    </>
  ),
  home: <path d="M3 11l9-7 9 7v9H3z" />,
  hourglass: <path d="M6 3h12M6 21h12M7 3c0 5 5 6 5 9s-5 4-5 9M17 3c0 5-5 6-5 9s5 4 5 9" />,
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v6M12 7.5v.5" />
    </>
  ),
  logOut: <path d="M9 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h3M16 8l4 4-4 4M20 12H10" />,
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
  plus: <path d="M12 5v14M5 12h14" />,
  moon: <path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" />,
  phone: (
    <>
      <rect x="7" y="2.5" width="10" height="19" rx="2" />
      <path d="M11 18h2" />
    </>
  ),
  pin: (
    <>
      <path d="M12 21s-6-5.5-6-11a6 6 0 0 1 12 0c0 5.5-6 11-6 11z" />
      <circle cx="12" cy="10" r="2" />
    </>
  ),
  play: <path d="M7 4.5v15l12-7.5z" fill="currentColor" stroke="none" />,
  question: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M9.5 9.5a2.5 2.5 0 0 1 5 0c0 1.5-2.5 2-2.5 3.5M12 17v.5" />
    </>
  ),
  satellite: (
    <>
      <rect x="9" y="9" width="6" height="6" rx="1" />
      <path d="M3 5l6 4M21 5l-6 4M3 19l6-4M21 19l-6-4" />
    </>
  ),
  scale: <path d="M5 9h14l-2 11H7zM9 9a3 3 0 0 1 6 0M12 13v3" />,
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
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </>
  ),
  stopSquare: <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" stroke="none" />,
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </>
  ),
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
