import type { CSSProperties } from "react";
import field from "../assets/wordmark-field.png";
import pilot from "../assets/wordmark-pilot.png";
import { en } from "../i18n/en";

// The lettering of the logo, cut into two masks (Field; Pilot with its leaf) and
// filled with the theme's ink and green, so it follows dark mode like any text.
function maskOf(url: string): CSSProperties {
  const mask = `url(${url}) center / contain no-repeat`;
  return { mask, WebkitMask: mask };
}

/** "FieldPilot" as the logo writes it, 24 px tall. */
export function Wordmark() {
  return (
    <span className="relative inline-block h-6 w-29 shrink-0">
      <span className="sr-only">{en.titles.app}</span>
      <span aria-hidden="true" className="absolute inset-0 bg-ink" style={maskOf(field)} />
      <span aria-hidden="true" className="absolute inset-0 bg-field" style={maskOf(pilot)} />
    </span>
  );
}
