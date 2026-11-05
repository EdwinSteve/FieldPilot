// The farm form's last step, as POST /plots takes it (docs/api.md §3.1). Pure logic only.
import type { NewPlot } from "../api/lifecycle";
import { areaHectares, middleOf, outlineProblem, type LatLng, type OutlineProblem } from "./farmOutline";

export type NameProblem = "missing";

export interface PlotProblems {
  outline: OutlineProblem | null;
  name: NameProblem | null;
  town: NameProblem | null;
  department: NameProblem | null;
}

/** The backend wants 2 to 80 characters for each name. */
const MIN_NAME = 2;
const MAX_NAME = 80;

function nameProblem(text: string): NameProblem | null {
  return text.trim().length < MIN_NAME ? "missing" : null;
}

export function plotProblems(
  outline: readonly LatLng[],
  name: string,
  town: string,
  department: string,
): PlotProblems {
  return {
    outline: outlineProblem(outline),
    name: nameProblem(name),
    town: nameProblem(town),
    department: nameProblem(department),
  };
}

export function hasProblem(problems: PlotProblems): boolean {
  return Object.values(problems).some((problem) => problem !== null);
}

const clip = (text: string) => text.trim().slice(0, MAX_NAME);

/** The plot to send; call only once `plotProblems` finds nothing. */
export function newPlot(outline: readonly LatLng[], name: string, town: string, department: string): NewPlot {
  const middle = middleOf(outline) ?? { lat: 0, lng: 0 };
  return {
    name: clip(name),
    municipality: clip(town),
    department: clip(department),
    latitude: Number(middle.lat.toFixed(6)),
    longitude: Number(middle.lng.toFixed(6)),
    area_ha: Number(areaHectares(outline).toFixed(2)),
  };
}
