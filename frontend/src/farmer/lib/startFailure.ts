// Why the backend did not start the crop the farmer said they planted (docs/api.md §5). Pure logic only.
import { ApiError } from "../../api/client";

/** "own_risk" is not a failure to show: it asks the farmer to confirm, then send again. */
export type StartFailure = "own_risk" | "active" | "date" | "noData" | "other";

const BY_CODE: Record<string, StartFailure> = {
  OwnRiskRequiredError: "own_risk",
  ActiveCycleExistsError: "active",
  InvalidSowingDateError: "date",
  MissingDataError: "noData",
};

export function startFailure(error: unknown): StartFailure {
  return error instanceof ApiError ? (BY_CODE[error.code] ?? "other") : "other";
}
