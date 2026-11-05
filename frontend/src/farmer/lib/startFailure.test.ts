import { describe, expect, it } from "vitest";
import { ApiError } from "../../api/client";
import { startFailure } from "./startFailure";

describe("startFailure", () => {
  it("asks for the own-risk confirmation on a crop outside the top three", () => {
    expect(startFailure(new ApiError(422, "OwnRiskRequiredError", "x"))).toBe("own_risk");
  });

  it("names the backend's other refusals", () => {
    expect(startFailure(new ApiError(409, "ActiveCycleExistsError", "x"))).toBe("active");
    expect(startFailure(new ApiError(422, "InvalidSowingDateError", "x"))).toBe("date");
    expect(startFailure(new ApiError(409, "MissingDataError", "x"))).toBe("noData");
  });

  it("falls back for anything else, a lost signal included", () => {
    expect(startFailure(new ApiError(500, "HttpError", "x"))).toBe("other");
    expect(startFailure(new TypeError("fetch failed"))).toBe("other");
  });
});
