// The harvest the farmer confirms, as POST /cycles/{id}/harvest takes it (D083, docs/api.md §6). Pure logic only.
import { ApiError } from "../../api/client";

export type Unit = "kg" | "bags";
export type Grade = "extra" | "first" | "second";

export const GRADES: readonly Grade[] = ["extra", "first", "second"];
/** The sack sizes most used for grain and potatoes; any other size can be typed. */
export const BAG_PRESETS: readonly number[] = [25, 50];
/** The backend's plausibility limit: 100 t per hectare of the plot. */
const MAX_KG_PER_HA = 100_000;

export type DateProblem = "missing" | "before_sowing" | "future";
export type AmountProblem = "missing" | "too_much";

export interface HarvestForm {
  date: string;
  /** What the farmer typed, in their unit. */
  amount: string;
  /** Null until the farmer chooses, when Settings says to ask each time. */
  unit: Unit | null;
  /** Kilograms in one of the farmer's bags, as they typed or chose it. */
  bagKg: string;
  grade: Grade | null;
}

export interface HarvestLimits {
  /** "2026-10-01": the harvest comes after it. */
  sowingDate: string;
  /** The plot's today: the harvest is not in the future. */
  today: string;
  areaHa: number;
}

export interface HarvestProblems {
  date: DateProblem | null;
  amount: AmountProblem | null;
  unit: "missing" | null;
  bag: "missing" | null;
  grade: "missing" | null;
}

/** "1.250,5" or "1250.5" as 1250.5; NaN for anything that is not a number. */
export function parseAmount(text: string): number {
  const clean = text.replace(/\s/g, "");
  if (!/^\d+([.,]\d+)?$/.test(clean)) return Number.NaN;
  return Number(clean.replace(",", "."));
}

/** What the amount field lets in: digits and one decimal mark. */
export function typedAmount(text: string): string {
  const digits = text.replace(/[^\d.,]/g, "");
  const mark = digits.search(/[.,]/);
  if (mark < 0) return digits.slice(0, 9);
  return `${digits.slice(0, mark).slice(0, 9)}${digits[mark]}${digits.slice(mark + 1).replace(/[.,]/g, "").slice(0, 2)}`;
}

/** The harvest in kilograms, or NaN while the form does not say. */
export function harvestKg(form: Pick<HarvestForm, "amount" | "unit" | "bagKg">): number {
  const amount = parseAmount(form.amount);
  if (form.unit === null) return Number.NaN;
  if (form.unit === "kg") return amount;
  return amount * parseAmount(form.bagKg);
}

export function harvestProblems(form: HarvestForm, limits: HarvestLimits): HarvestProblems {
  const kg = harvestKg(form);
  const bagKg = parseAmount(form.bagKg);
  return {
    date: dateProblem(form.date, limits),
    amount: !(parseAmount(form.amount) > 0)
      ? "missing"
      : kg > limits.areaHa * MAX_KG_PER_HA
        ? "too_much"
        : null,
    unit: form.unit === null ? "missing" : null,
    bag: form.unit === "bags" && !(bagKg > 0) ? "missing" : null,
    grade: form.grade === null ? "missing" : null,
  };
}

function dateProblem(date: string, limits: HarvestLimits): DateProblem | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return "missing";
  if (date <= limits.sowingDate) return "before_sowing";
  return date > limits.today ? "future" : null;
}

export function hasProblem(problems: HarvestProblems): boolean {
  return Object.values(problems).some((problem) => problem !== null);
}

/** "2,000" for the total line. */
export function kgText(kg: number): string {
  return Math.round(kg).toLocaleString("en-US");
}

/** Why the backend did not record the harvest. */
export type HarvestFailure = "open_tasks" | "already" | "invalid" | "other";

const BY_CODE: Record<string, HarvestFailure> = {
  OpenTasksError: "open_tasks",
  InvalidTransitionError: "already",
  InvalidHarvestError: "invalid",
};

export function harvestFailure(error: unknown): HarvestFailure {
  return error instanceof ApiError ? (BY_CODE[error.code] ?? "other") : "other";
}
