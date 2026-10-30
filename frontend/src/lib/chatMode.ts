// Which chat failure means "mock mode", not a passing outage (D063, D072).
import { ApiError } from "../api/client";

/** The backend's error code when the chat is off under MOCK_LLM=1. */
export const CHAT_UNAVAILABLE_CODE = "ChatUnavailableError";

/** True only for the mock-mode 503, so a real outage still shows its error. */
export function isMockModeChatError(error: unknown): boolean {
  return (
    error instanceof ApiError && error.status === 503 && error.code === CHAT_UNAVAILABLE_CODE
  );
}
