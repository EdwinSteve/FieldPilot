import { describe, expect, it } from "vitest";
import { ApiError } from "../../api/client";
import { actionFailure } from "./actionFailure";

describe("actionFailure", () => {
  it("blames the signal when the phone is offline", () => {
    expect(actionFailure(new ApiError(409, "Conflict", "x"), false)).toBe("offline");
    expect(actionFailure(new TypeError("Failed to fetch"), false)).toBe("offline");
  });

  it("calls a request that never got an answer unreachable", () => {
    expect(actionFailure(new TypeError("Failed to fetch"), true)).toBe("unreachable");
  });

  it("calls a gateway error unreachable: the farm itself never answered", () => {
    expect(actionFailure(new ApiError(502, "HttpError", "x"), true)).toBe("unreachable");
    expect(actionFailure(new ApiError(504, "HttpError", "x"), true)).toBe("unreachable");
  });

  it("calls any other answer from the farm a refusal", () => {
    expect(actionFailure(new ApiError(409, "Conflict", "x"), true)).toBe("rejected");
    expect(actionFailure(new ApiError(500, "Oops", "x"), true)).toBe("rejected");
  });
});
