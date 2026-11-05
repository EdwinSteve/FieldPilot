// The backend's Spanish names, as the English UI shows them. Pure logic only.
import { en } from "../i18n/en";

/** "Zona 2" reads "Zone 2". The number comes from the name: Zona 2 has id 1 in the seed. */
export function zoneLabel(name: string): string {
  return name.replace(/^Zona\b/, en.names.zone);
}

/** "Finca demo, Neiva" reads "Finca demo". */
export function farmLabel(plotName: string): string {
  return plotName.split(",")[0]?.trim() ?? plotName;
}

/** The crop's name, or its code in words for a crop the app has no name for yet. */
export function cropLabel(crop: string): string {
  return en.names.crops[crop] ?? crop.replaceAll("_", " ");
}
