import type { HealthResponse } from "../types/health";
import { getJson } from "./client";

export function fetchHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/health");
}
