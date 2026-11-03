// Why the market refused a farmer's step, so the sheet can say what to do. Pure logic only.
import { ApiError } from "../../api/client";

export type MarketFailure = "too_low" | "already" | "bad_offer" | "not_yours" | "offline" | "other";

const BY_CODE: Record<string, MarketFailure> = {
  PriceTooLowError: "too_low",
  ListingStateError: "already",
  InvalidOfferError: "bad_offer",
  ForbiddenError: "not_yours",
};

export function marketFailure(error: unknown, online: boolean): MarketFailure {
  if (!online) return "offline";
  return error instanceof ApiError ? (BY_CODE[error.code] ?? "other") : "other";
}
