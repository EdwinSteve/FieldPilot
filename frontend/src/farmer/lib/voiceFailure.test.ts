import { describe, expect, it } from "vitest";
import { ApiError } from "../../api/client";
import { micFailure, sendFailure } from "./voiceFailure";

describe("micFailure", () => {
  it("tells a refused permission from a missing mic", () => {
    expect(micFailure(new DOMException("no", "NotAllowedError"))).toBe("mic_blocked");
    expect(micFailure(new DOMException("none", "NotFoundError"))).toBe("mic_missing");
  });

  it("reads an http page's missing mediaDevices as a missing mic", () => {
    expect(micFailure(new TypeError("undefined"))).toBe("mic_missing");
  });
});

describe("sendFailure", () => {
  it.each([
    [new ApiError(503, "ChatUnavailableError", "m"), "needs_live_model"],
    [new ApiError(422, "NothingHeardError", "m"), "not_heard"],
    [new ApiError(422, "UnsupportedAudioError", "m"), "not_heard"],
    [new ApiError(503, "LLMUnavailableError", "m"), "service_busy"],
    [new ApiError(503, "SpeechUnavailableError", "m"), "service_busy"],
    [new ApiError(500, "Oops", "m"), "unknown"],
    [new DOMException("too short", "EncodingError"), "not_heard"],
    [new TypeError("network"), "unknown"],
  ])("reads %s as %s", (error, failure) => {
    expect(sendFailure(error)).toBe(failure);
  });
});
