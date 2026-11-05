// What a farmer's yes actually led to: the backend may still refuse or wait (D062).
import type { TaskStatus } from "../../types/api";

export type ApprovalOutcome = "running" | "planned" | "not_run";

export function approvalOutcome(status: TaskStatus): ApprovalOutcome {
  if (status === "executed") return "running";
  return status === "scheduled" ? "planned" : "not_run";
}
