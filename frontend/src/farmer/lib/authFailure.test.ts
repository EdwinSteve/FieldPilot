import { describe, expect, it } from "vitest";
import { ApiError } from "../../api/client";
import { authFailure } from "./authFailure";

describe("authFailure", () => {
  it("names each refusal the backend sends", () => {
    expect(authFailure(new ApiError(401, "InvalidCredentialsError", "x"), true)).toBe("wrong");
    expect(authFailure(new ApiError(423, "AccountLockedError", "x"), true)).toBe("locked");
    expect(authFailure(new ApiError(409, "PhoneTakenError", "x"), true)).toBe("phone_taken");
    expect(authFailure(new ApiError(422, "WeakPasswordError", "x"), true)).toBe("weak_password");
    expect(authFailure(new ApiError(422, "InvalidPhoneError", "x"), true)).toBe("invalid_phone");
    expect(authFailure(new ApiError(409, "StalePolicyError", "x"), true)).toBe("policy_changed");
  });

  it("tells no signal from a farm that does not answer", () => {
    expect(authFailure(new TypeError("fetch failed"), false)).toBe("offline");
    expect(authFailure(new TypeError("fetch failed"), true)).toBe("unreachable");
    expect(authFailure(new ApiError(502, "HttpError", "x"), true)).toBe("unreachable");
  });

  it("falls back for anything else", () => {
    expect(authFailure(new ApiError(500, "HttpError", "x"), true)).toBe("other");
  });
});
