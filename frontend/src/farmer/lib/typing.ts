// What each field lets the farmer type, so a wrong key never lands. Pure logic only.

/** The backend's limits (D082, D083). */
export const MAX_NAME = 120;
export const MAX_FARM_NAME = 80;
export const MAX_PASSWORD = 128;
/** A Colombian mobile without +57: 10 digits. */
export const MOBILE_DIGITS = 10;

/** A person's name: letters in any alphabet, spaces, and ' - . as in "O'Neil" or "Ma. José". */
export function typedName(text: string): string {
  return text.replace(/[^\p{L}\p{M} '.-]/gu, "").replace(/ {2,}/g, " ").slice(0, MAX_NAME);
}

/** A farm's name: a name that may also carry numbers, as in "Lote 3". */
export function typedFarmName(text: string): string {
  return text.replace(/[^\p{L}\p{M}\d ',.-]/gu, "").replace(/ {2,}/g, " ").slice(0, MAX_FARM_NAME);
}

/**
 * The 10 digits of a mobile, whatever was typed or pasted. A pasted "+57 300…"
 * or "57300…" loses its country code, which the field already shows.
 */
export function typedMobile(text: string): string {
  const digits = text.replace(/\D/g, "");
  const local = digits.length > MOBILE_DIGITS && digits.startsWith("57") ? digits.slice(2) : digits;
  return local.slice(0, MOBILE_DIGITS);
}

/** "3001234567" shown as "300 123 4567", the way Colombians write it. */
export function mobileDisplay(digits: string): string {
  return [digits.slice(0, 3), digits.slice(3, 6), digits.slice(6)].filter(Boolean).join(" ");
}
