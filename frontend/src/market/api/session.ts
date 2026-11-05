// The marketplace's login: the same D082 flow as the farmer app, in its own storage, so a
// shopper and a farmer on one computer never share a session.
import { apiUrl, getJson, postJson, type Session } from "../../api/client";
import { fromStoredUser, toStoredUser, type MarketUser, type StoredUser } from "../lib/storedUser";

const KEY = "fieldpilot.market.session";

interface TokenPair {
  access_token: string;
  refresh_token: string;
}

interface UserOut {
  id: number;
  phone: string;
  full_name: string;
  role: MarketUser["role"];
}

function read(): string | null {
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

function write(value: string | null): void {
  try {
    if (value === null) window.localStorage.removeItem(KEY);
    else window.localStorage.setItem(KEY, value);
  } catch {
    // Private mode: the login lasts until the page closes.
  }
}

const userOf = (user: UserOut): MarketUser => ({ id: user.id, name: user.full_name, phone: user.phone, role: user.role });

class MarketSession implements Session {
  private access: string | null = null;
  private stored: StoredUser | null = fromStoredUser(read());
  private renewing: Promise<boolean> | null = null;
  private readonly listeners = new Set<() => void>();

  readonly subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  readonly current = (): StoredUser | null => this.stored;

  headers(): Record<string, string> {
    return this.access === null ? {} : { Authorization: `Bearer ${this.access}` };
  }

  /**
   * Waits for an access token when a login is saved but none is in memory yet, as after a reload.
   * With AUTH_REQUIRED=0 the backend never answers 401, so a 401-driven renewal alone would leave
   * calls running as the anonymous demo farmer, which the market refuses (D082, D085).
   */
  async ensureAccess(): Promise<void> {
    if (this.access === null && this.stored !== null) await this.renew();
  }

  /** One refresh for every call that got a 401: a refresh token is good once. */
  renew(): Promise<boolean> {
    if (this.stored === null) return Promise.resolve(false);
    this.renewing ??= this.refresh(this.stored).finally(() => {
      this.renewing = null;
    });
    return this.renewing;
  }

  async logIn(phone: string, password: string): Promise<MarketUser> {
    const pair = await postJson<TokenPair>("/auth/login", { phone, password });
    this.access = pair.access_token;
    const user = userOf(await getJson<UserOut>("/auth/me"));
    this.keep(pair, user);
    return user;
  }

  async register(form: { phone: string; full_name: string; password: string; privacy_policy_version: string }) {
    const { user, tokens } = await postJson<{ user: UserOut; tokens: TokenPair }>("/auth/register", {
      ...form,
      role: "customer",
      accept_privacy_policy: true,
    });
    this.keep(tokens, userOf(user));
  }

  async logOut(): Promise<void> {
    const refreshToken = this.stored?.refreshToken;
    try {
      if (refreshToken !== undefined) await postJson<undefined>("/auth/logout", { refresh_token: refreshToken });
    } catch {
      // Offline or already ended: the tokens are dropped here either way.
    }
    this.end();
  }

  private async refresh(stored: StoredUser): Promise<boolean> {
    let response: Response;
    try {
      response = await fetch(apiUrl("/auth/refresh"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: stored.refreshToken }),
      });
    } catch {
      return false;
    }
    if (response.status === 401) {
      this.end();
      return false;
    }
    if (!response.ok) return false;
    this.keep((await response.json()) as TokenPair, stored.user);
    return true;
  }

  private keep(pair: TokenPair, user: MarketUser): void {
    this.access = pair.access_token;
    const same = this.stored?.user.id === user.id;
    this.stored = { refreshToken: pair.refresh_token, user };
    write(toStoredUser(this.stored));
    if (!same) this.notify();
  }

  private end(): void {
    this.access = null;
    this.stored = null;
    write(null);
    this.notify();
  }

  private notify(): void {
    this.listeners.forEach((listener) => listener());
  }
}

export const session = new MarketSession();
