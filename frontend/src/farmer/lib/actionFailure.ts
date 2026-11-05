// Why a tap did not reach the farm, so the notice can say what to do. Pure logic only.
import { ApiError } from "../../api/client";

export type ActionFailure = "offline" | "unreachable" | "rejected";

/** Gateway answers mean the server behind the proxy is down, not that it said no. */
const GATEWAY_STATUSES = new Set([502, 503, 504]);

export function actionFailure(error: unknown, online: boolean): ActionFailure {
  if (!online) return "offline";
  if (!(error instanceof ApiError)) return "unreachable";
  return GATEWAY_STATUSES.has(error.status) ? "unreachable" : "rejected";
}
