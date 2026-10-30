// Hand-drawn stroke icons for the dashboard (D068: no icon library).
// Decorative only: the text next to them always carries the meaning.
import type { ReactNode } from "react";

export type IconName =
  | "drop"
  | "leaf"
  | "satellite"
  | "clock"
  | "shield"
  | "valve"
  | "mic"
  | "alert";

const PATHS: Record<IconName, ReactNode> = {
  drop: <path d="M12 3.5c2.8 3.8 5.5 6.8 5.5 10a5.5 5.5 0 1 1-11 0c0-3.2 2.7-6.2 5.5-10z" />,
  leaf: (
    <>
      <path d="M5.5 18.5C5.5 11 11 5.5 18.5 5.5c0 7.5-5.5 13-13 13z" />
      <path d="M5.5 18.5C8.5 14.5 12.5 10.5 16.5 7.5" />
    </>
  ),
  satellite: (
    <>
      <rect x="10" y="10.5" width="4" height="3" rx="0.8" />
      <path d="M10 12H6.5M21 12h-7" />
      <rect x="2" y="9.5" width="4.5" height="5" rx="0.6" />
      <rect x="17.5" y="9.5" width="4.5" height="5" rx="0.6" />
      <path d="M12 10.5V8" />
      <circle cx="12" cy="6.4" r="1" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 8v4l2.8 1.8" />
    </>
  ),
  shield: (
    <>
      <path d="M12 3.5l6.5 2.6v5.2c0 4.2-2.8 7-6.5 8.7-3.7-1.7-6.5-4.5-6.5-8.7V6.1z" />
      <path d="M9.2 11.8l2 2 3.8-3.8" />
    </>
  ),
  valve: (
    <>
      <path d="M3.5 8.5L10 12l-6.5 3.5zM20.5 8.5L14 12l6.5 3.5z" />
      <path d="M12 12V6" />
      <path d="M8.5 6h7" />
    </>
  ),
  mic: (
    <>
      <rect x="9" y="3.5" width="6" height="9.5" rx="3" />
      <path d="M6 11.5a6 6 0 0 0 12 0" />
      <path d="M12 17.5V21" />
    </>
  ),
  alert: (
    <>
      <path d="M12 4.5L20.5 19h-17z" />
      <path d="M12 10v4" />
      <circle cx="12" cy="16.8" r="1" fill="currentColor" stroke="none" />
    </>
  ),
};

interface IconProps {
  name: IconName;
  size?: number;
}

/** A small line icon. Hidden from assistive technology; text says what it means. */
export function Icon({ name, size = 18 }: IconProps) {
  return (
    <svg
      className="icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {PATHS[name]}
    </svg>
  );
}
