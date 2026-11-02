// Why a question failed, in terms the farmer can act on. Pure logic only.
import { ApiError } from "../../api/client";
import { isMockModeChatError } from "../../lib/mockMode";

export type TalkFailure =
  | "mic_blocked"
  | "mic_missing"
  | "not_heard"
  | "needs_live_model"
  | "service_busy"
  | "unknown";

const UNPROCESSABLE = 422;
const UNAVAILABLE = 503;

/** Why the microphone would not open. An http page has no `mediaDevices` at all. */
export function micFailure(error: unknown): TalkFailure {
  const blocked = error instanceof DOMException && error.name === "NotAllowedError";
  return blocked ? "mic_blocked" : "mic_missing";
}

/** Why a question got no answer. Audio too short to decode was not heard either. */
export function sendFailure(error: unknown): TalkFailure {
  if (isMockModeChatError(error)) return "needs_live_model";
  if (error instanceof DOMException) return "not_heard";
  if (!(error instanceof ApiError)) return "unknown";
  if (error.status === UNPROCESSABLE) return "not_heard";
  return error.status === UNAVAILABLE ? "service_busy" : "unknown";
}
