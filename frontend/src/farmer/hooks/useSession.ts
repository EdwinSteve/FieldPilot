import { useSyncExternalStore } from "react";
import { session } from "../api/session";
import type { Farmer } from "../lib/account";
import type { KnownFarmer } from "../lib/storedSession";

export interface SessionControl {
  /** The signed-in farmer, or null when signed out. */
  farmer: Farmer | null;
  /** Who last used this phone, kept after Sign out so Start opens the log-in; never shown. */
  known: KnownFarmer | null;
  logIn: typeof session.logIn;
  register: typeof session.register;
  logOut: () => Promise<void>;
}

/** The login of this tab (see api/session), re-rendering on sign-in and sign-out only. */
export function useSession(): SessionControl {
  const stored = useSyncExternalStore(session.subscribe, session.current);
  return {
    farmer: stored?.farmer ?? null,
    known: session.knownFarmer(),
    logIn: (phone, password) => session.logIn(phone, password),
    register: (form, home) => session.register(form, home),
    logOut: () => session.logOut(),
  };
}
