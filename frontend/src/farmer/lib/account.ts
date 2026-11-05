// The sign-up and log-in forms' rules, as the backend checks them (D082). Pure logic only.
//
// The backend checks every rule again; these say what is wrong before the farmer waits.

export type FieldProblem =
  | "name_short"
  | "phone_invalid"
  | "password_missing"
  | "password_short"
  | "password_long"
  | "password_has_phone"
  | "password_mismatch"
  | "department_missing"
  | "town_missing"
  | "consent_missing";

/** The farmer as the backend knows them, kept so the log-in can greet them. */
export interface Farmer {
  id: number;
  name: string;
  /** "+573001234567", as the backend stores it. */
  phone: string;
}

const MIN_NAME = 2;
const MAX_NAME = 120;
/** config/identity.yaml and MAX_PASSWORD_LENGTH in the backend. */
const MIN_PASSWORD = 10;
const MAX_PASSWORD = 128;
/** A Colombian mobile: 10 digits starting with 3, with or without +57. */
const MOBILE = /^(?:57)?(3\d{9})$/;

/** "300 123-4567" or "+57 300 123 4567" as "3001234567"; null when it is not a Colombian mobile. */
export function colombianMobile(text: string): string | null {
  return MOBILE.exec(text.replace(/[\s\-+().]/g, ""))?.[1] ?? null;
}

export function nameProblem(name: string): FieldProblem | null {
  const length = name.trim().length;
  return length < MIN_NAME || length > MAX_NAME ? "name_short" : null;
}

export function phoneProblem(text: string): FieldProblem | null {
  return colombianMobile(text) === null ? "phone_invalid" : null;
}

export function passwordProblem(password: string, phone: string): FieldProblem | null {
  if (password.length < MIN_PASSWORD) return "password_short";
  if (password.length > MAX_PASSWORD) return "password_long";
  const mobile = colombianMobile(phone);
  return mobile !== null && password.includes(mobile) ? "password_has_phone" : null;
}

/** The second password must match the first; a wrong first one is reported on its own. */
export function passwordAgainProblem(
  password: string,
  again: string,
  phone: string,
): FieldProblem | null {
  return passwordProblem(password, phone) === null && password !== again
    ? "password_mismatch"
    : null;
}

/** The log-in checks only that something was typed: the backend says whether it is right. */
export function passwordMissing(password: string): FieldProblem | null {
  return password === "" ? "password_missing" : null;
}

/** Where the farmer lives is chosen from the list: a department, then one of its towns. */
export function homeProblems(department: string, town: string) {
  return {
    department: department === "" ? ("department_missing" as const) : null,
    town: department !== "" && town === "" ? ("town_missing" as const) : null,
  };
}

export function consentProblem(accepted: boolean): FieldProblem | null {
  return accepted ? null : "consent_missing";
}
