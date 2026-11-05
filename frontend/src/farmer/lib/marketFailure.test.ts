import { describe, expect, it } from "vitest";
import { ApiError } from "../../api/client";
import { marketFailure } from "./marketFailure";

describe("marketFailure", () => {
  it("names the market's refusals", () => {
    expect(marketFailure(new ApiError(422, "PriceTooLowError", "x"), true)).toBe("too_low");
    expect(marketFailure(new ApiError(409, "ListingStateError", "x"), true)).toBe("already");
    expect(marketFailure(new ApiError(403, "ForbiddenError", "x"), true)).toBe("not_yours");
    expect(marketFailure(new ApiError(422, "InvalidOfferError", "x"), true)).toBe("bad_offer");
    expect(marketFailure(new ApiError(500, "Boom", "x"), true)).toBe("other");
  });

  it("says no signal before anything else", () => {
    expect(marketFailure(new TypeError("fetch failed"), false)).toBe("offline");
  });
});
