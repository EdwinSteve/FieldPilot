// Which failures mean "mock mode", not a passing outage (D063, D072, D074).
import { ApiError } from "../api/client";

/** The backend's error code when the chat is off under MOCK_LLM=1. */
export const CHAT_UNAVAILABLE_CODE = "ChatUnavailableError";

/** The backend's error code when the recorded day fits no farm but the fresh one. */
export const FIXTURE_EXHAUSTED_CODE = "FixtureExhaustedError";

/** True only for the mock-mode 503, so a real outage still shows its error. */
export function isMockModeChatError(error: unknown): boolean {
  return (
    error instanceof ApiError && error.status === 503 && error.code === CHAT_UNAVAILABLE_CODE
  );
}

/** True only when the recorded demo day cannot replay on this farm. */
export function isFixtureExhausted(error: unknown): boolean {
  return (
    error instanceof ApiError && error.status === 503 && error.code === FIXTURE_EXHAUSTED_CODE
  );
}
