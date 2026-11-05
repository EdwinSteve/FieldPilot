// Where the setup answers live on this phone; api/session clears them on Sign out.
import { fromStoredDraft, toStoredDraft, type SetupDraft } from "../lib/setupDraft";

const DRAFT_KEY = "fieldpilot.setup";

export function readDraft(): SetupDraft {
  try {
    return fromStoredDraft(window.localStorage.getItem(DRAFT_KEY));
  } catch {
    return fromStoredDraft(null);
  }
}

export function saveDraft(draft: SetupDraft): void {
  try {
    window.localStorage.setItem(DRAFT_KEY, toStoredDraft(draft));
  } catch {
    // Private mode: the answers last while the screen is open.
  }
}
