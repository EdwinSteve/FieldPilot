// Why the backend turned a form down, as words the farmer can act on. Pure logic only.
import { ApiError } from "../../api/client";

export type AuthFailure =
  | "wrong"
  | "locked"
  | "phone_taken"
  | "weak_password"
  | "invalid_phone"
  | "policy_changed"
  | "offline"
  | "unreachable"
  | "other";

/** The backend's error classes (docs/api.md §2), each as one failure. */
const BY_CODE: Record<string, AuthFailure> = {
  InvalidCredentialsError: "wrong",
  AccountLockedError: "locked",
  PhoneTakenError: "phone_taken",
  WeakPasswordError: "weak_password",
  InvalidPhoneError: "invalid_phone",
  StalePolicyError: "policy_changed",
};

const GATEWAY_STATUSES = new Set([502, 503, 504]);

export function authFailure(error: unknown, online: boolean): AuthFailure {
  if (!online) return "offline";
  if (!(error instanceof ApiError)) return "unreachable";
  if (GATEWAY_STATUSES.has(error.status)) return "unreachable";
  return BY_CODE[error.code] ?? "other";
}
