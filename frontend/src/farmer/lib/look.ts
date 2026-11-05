// How the app looks on this phone: light or dark, and how big the text is. Pure logic only.

/** "phone" follows the phone's own light or dark setting. */
export type ThemeChoice = "phone" | "light" | "dark";
export type Theme = "light" | "dark";
export type TextSize = "normal" | "large";

export interface Look {
  theme: ThemeChoice;
  text: TextSize;
}

export const THEMES: readonly ThemeChoice[] = ["phone", "light", "dark"];
export const TEXT_SIZES: readonly TextSize[] = ["normal", "large"];
export const DEFAULT_LOOK: Look = { theme: "phone", text: "normal" };

const VERSION = 1;

export function toStoredLook(look: Look): string {
  return JSON.stringify({ version: VERSION, ...look });
}

/** The saved look; each part it cannot trust falls back to the default on its own. */
export function fromStoredLook(text: string | null): Look {
  let value: Record<string, unknown> | null = null;
  try {
    const parsed: unknown = text === null ? null : JSON.parse(text);
    if (typeof parsed === "object" && parsed !== null) value = parsed as Record<string, unknown>;
  } catch {
    value = null;
  }
  if (value?.version !== VERSION) return DEFAULT_LOOK;
  return {
    theme: THEMES.find((theme) => theme === value.theme) ?? DEFAULT_LOOK.theme,
    text: TEXT_SIZES.find((size) => size === value.text) ?? DEFAULT_LOOK.text,
  };
}

/** The theme on screen: the farmer's choice, or the phone's when they left it to the phone. */
export function themeOf(choice: ThemeChoice, phoneDark: boolean): Theme {
  if (choice === "phone") return phoneDark ? "dark" : "light";
  return choice;
}
