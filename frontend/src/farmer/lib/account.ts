// The demo account kept on this phone. Pure logic only.
//
// This is not security: the backend has no sign-in, and anyone with the URL can
// still reach the farm. The PIN is hashed only so it is never stored as typed.

export interface Account {
  name: string;
  /** Digits only, with a leading + kept. */
  phone: string;
  salt: string;
  pinHash: string;
}

export type FieldProblem =
  | "name_missing"
  | "phone_short"
  | "phone_long"
  | "pin_length"
  | "pin_mismatch";

export type LogInResult = "ok" | "no_account" | "wrong";

const VERSION = 1;
const PIN_LENGTH = 4;
/** ITU numbers run 8 to 15 digits once spaces and dashes are gone. */
const MIN_PHONE_DIGITS = 8;
const MAX_PHONE_DIGITS = 15;
const HASH_ROUNDS = 1000;
const FNV_OFFSET = 0x811c9dc5;
const FNV_PRIME = 0x01000193;

/** "+57 300-123 4567" as "+573001234567": the same number however it is typed. */
export function normalPhone(text: string): string {
  const trimmed = text.trim();
  const digits = trimmed.replace(/\D/g, "");
  return trimmed.startsWith("+") ? `+${digits}` : digits;
}

export function nameProblem(name: string): FieldProblem | null {
  return name.trim() === "" ? "name_missing" : null;
}

export function phoneProblem(text: string): FieldProblem | null {
  const digits = normalPhone(text).replace("+", "").length;
  if (digits < MIN_PHONE_DIGITS) return "phone_short";
  return digits > MAX_PHONE_DIGITS ? "phone_long" : null;
}

export function pinProblem(pin: string): FieldProblem | null {
  return new RegExp(`^\\d{${PIN_LENGTH}}$`).test(pin) ? null : "pin_length";
}

/** The second PIN must match the first; a wrong first PIN is reported on its own. */
export function pinAgainProblem(pin: string, again: string): FieldProblem | null {
  return pinProblem(pin) === null && pin !== again ? "pin_mismatch" : null;
}

function fnv1a(text: string, seed: number): number {
  let hash = seed;
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, FNV_PRIME) >>> 0;
  }
  return hash;
}

/** A repeated FNV-1a: enough that the PIN is not stored as typed, far short of real security. */
export function hashPin(pin: string, salt: string): string {
  let hash = FNV_OFFSET;
  for (let round = 0; round < HASH_ROUNDS; round += 1) {
    hash = fnv1a(`${salt}:${pin}:${round}`, hash);
  }
  return hash.toString(16).padStart(8, "0");
}

export function newAccount(name: string, phone: string, pin: string, salt: string): Account {
  return { name: name.trim(), phone: normalPhone(phone), salt, pinHash: hashPin(pin, salt) };
}

export function logInResult(account: Account | null, phone: string, pin: string): LogInResult {
  if (account === null) return "no_account";
  const matches =
    account.phone === normalPhone(phone) && account.pinHash === hashPin(pin, account.salt);
  return matches ? "ok" : "wrong";
}

export function toStoredAccount(account: Account): string {
  return JSON.stringify({ version: VERSION, ...account });
}

/** Null for anything this version of the app did not write. */
export function fromStoredAccount(text: string | null): Account | null {
  if (text === null) return null;
  try {
    const parsed = JSON.parse(text) as Record<string, unknown>;
    const { name, phone, salt, pinHash } = parsed;
    if (parsed.version !== VERSION) return null;
    if (typeof name !== "string" || typeof phone !== "string") return null;
    if (typeof salt !== "string" || typeof pinHash !== "string") return null;
    return { name, phone, salt, pinHash };
  } catch {
    return null;
  }
}
