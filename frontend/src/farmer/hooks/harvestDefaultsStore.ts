// How this farmer counts a harvest; api/session clears it on Sign out.
import { fromStoredHarvest, toStoredHarvest, type HarvestDefaults } from "../lib/harvestDefaults";

const HARVEST_KEY = "fieldpilot.harvest";

export function readHarvestDefaults(): HarvestDefaults {
  try {
    return fromStoredHarvest(window.localStorage.getItem(HARVEST_KEY));
  } catch {
    return fromStoredHarvest(null);
  }
}

export function saveHarvestDefaults(defaults: HarvestDefaults): void {
  try {
    window.localStorage.setItem(HARVEST_KEY, toStoredHarvest(defaults));
  } catch {
    // Private mode: the form opens with the usual bags of 50 kg.
  }
}
