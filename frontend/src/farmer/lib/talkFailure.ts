// Why a question failed, in terms the farmer can act on. Pure logic only.
import { ApiError } from "../../api/client";
import { isMockModeChatError } from "../../lib/mockMode";

export type TalkFailure =
  | "mic_blocked"
  | "mic_missing"
  | "not_heard"
  | "needs_live_model"
  | "service_busy"
  | "needs_automated_crop"
  | "unknown";

const UNPROCESSABLE = 422;
const UNAVAILABLE = 503;
const CONFLICT = 409;

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
  // The chat answers only about a crop FieldPilot looks after (D083): a manual crop, or none, gets 409.
  if (error.status === CONFLICT && error.code === "MissingDataError") return "needs_automated_crop";
  return error.status === UNAVAILABLE ? "service_busy" : "unknown";
}
