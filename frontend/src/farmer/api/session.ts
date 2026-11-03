// The farmer's login: the tokens, one renewal at a time, and who is signed in (D082, docs/api.md §2).
import { apiUrl, type Session } from "../../api/client";
import type { Farmer } from "../lib/account";
import type { Home } from "../lib/places";
import {
  fromKnownFarmer,
  fromStoredSession,
  toKnownFarmer,
  toStoredSession,
  type KnownFarmer,
  type StoredSession,
} from "../lib/storedSession";
import { lifecycle, type Registration, type TokenPair, type User } from "./lifecycle";

const SESSION_KEY = "fieldpilot.session";
const KNOWN_KEY = "fieldpilot.known";
/** What one farmer's visit leaves behind; the next person on this phone must not see it. */
const PRIVATE_KEYS = ["fieldpilot.farm", "fieldpilot.setup"];
const PRIVATE_SESSION_KEYS = ["fieldpilot.chat"];

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string | null, storage: "local" | "session" = "local"): void {
  try {
    const store = storage === "local" ? window.localStorage : window.sessionStorage;
    if (value === null) store.removeItem(key);
    else store.setItem(key, value);
  } catch {
    // Private mode or a full disk: the login lasts until the page closes.
  }
}

function farmerOf(user: User): Farmer {
  return { id: user.id, name: user.full_name, phone: user.phone };
}

class SessionKeeper implements Session {
  /** Only in memory: a reload renews it from the refresh token. */
  private access: string | null = null;
  private stored: StoredSession | null = fromStoredSession(read(SESSION_KEY));
  private known: KnownFarmer | null = fromKnownFarmer(read(KNOWN_KEY));
  private renewing: Promise<boolean> | null = null;
  private readonly listeners = new Set<() => void>();

  readonly subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  /** Changes identity only when the farmer signs in or out, as useSyncExternalStore needs. */
  readonly current = (): StoredSession | null => this.stored;

  readonly knownFarmer = (): KnownFarmer | null => this.known;

  headers(): Record<string, string> {
    return this.access === null ? {} : { Authorization: `Bearer ${this.access}` };
  }

  /** One refresh for every call that got a 401: a refresh token sent twice ends every session. */
  renew(): Promise<boolean> {
    if (this.stored === null) return Promise.resolve(false);
    this.renewing ??= this.refresh(this.stored).finally(() => {
      this.renewing = null;
    });
    return this.renewing;
  }

  async logIn(phone: string, password: string): Promise<void> {
    const pair = await lifecycle.logIn(phone, password);
    this.access = pair.access_token;
    const user = await lifecycle.me();
    this.keep(pair, farmerOf(user), this.known?.phone === user.phone ? this.known.home : null);
  }

  async register(form: Omit<Registration, "role" | "accept_privacy_policy">, home: Home) {
    const { user, tokens } = await lifecycle.register({
      ...form,
      role: "farmer",
      accept_privacy_policy: true,
    });
    this.keep(tokens, farmerOf(user), home);
  }

  /** Ends the session here and on the backend; the farmer stays known so Start opens the log-in. */
  async logOut(): Promise<void> {
    const refreshToken = this.stored?.refreshToken;
    try {
      if (refreshToken !== undefined) await lifecycle.logOut(refreshToken);
    } catch {
      // Offline or already ended: the tokens are dropped here either way.
    }
    this.end();
  }

  /** An image the farm sends, such as the satellite photo, which an <img> cannot ask for with a token. */
  async blob(url: string): Promise<Blob> {
    const send = () => fetch(url, { headers: this.headers() });
    let response = await send();
    if (response.status === 401 && (await this.renew())) response = await send();
    if (!response.ok) throw new Error(`GET ${url} failed (HTTP ${response.status})`);
    return response.blob();
  }

  private async refresh(stored: StoredSession): Promise<boolean> {
    let response: Response;
    try {
      response = await fetch(apiUrl("/auth/refresh"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: stored.refreshToken }),
      });
    } catch {
      return false; // No signal: the session may still be good once it comes back.
    }
    if (response.status === 401) {
      this.end(); // The refresh token is spent or revoked: the session is over.
      return false;
    }
    if (!response.ok) return false;
    this.keep((await response.json()) as TokenPair, stored.farmer, this.known?.home ?? null);
    return true;
  }

  private keep(pair: TokenPair, farmer: Farmer, home: Home | null): void {
    this.access = pair.access_token;
    const signedIn = this.stored?.farmer.id === farmer.id;
    this.stored = { refreshToken: pair.refresh_token, farmer };
    write(SESSION_KEY, toStoredSession(this.stored));
    this.known = { name: farmer.name, phone: farmer.phone, home };
    write(KNOWN_KEY, toKnownFarmer(this.known));
    // A renewal is not news to the screens; a sign-in is.
    if (!signedIn) this.notify();
  }

  private end(): void {
    this.access = null;
    this.stored = null;
    write(SESSION_KEY, null);
    PRIVATE_KEYS.forEach((key) => write(key, null));
    PRIVATE_SESSION_KEYS.forEach((key) => write(key, null, "session"));
    this.notify();
  }

  private notify(): void {
    this.listeners.forEach((listener) => listener());
  }
}

/** The one session of this tab, joined to every API call by main.tsx. */
export const session = new SessionKeeper();
