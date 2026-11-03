import { useState } from "react";
import {
  fromStoredAccount,
  logInResult,
  newAccount,
  toStoredAccount,
  type Account,
  type LogInResult,
} from "../lib/account";

const ACCOUNT_KEY = "fieldpilot.account";
/** Holds the phone that is signed in; gone after Sign out. */
const SESSION_KEY = "fieldpilot.session";
const SALT_BYTES = 8;

export interface AccountControl {
  account: Account | null;
  signedIn: boolean;
  signUp: (name: string, phone: string, pin: string) => void;
  logIn: (phone: string, pin: string) => LogInResult;
  signOut: () => void;
}

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string | null): void {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    // Private mode or a full disk: the sign-in lasts until the page closes.
  }
}

function newSalt(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(SALT_BYTES));
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

/** The demo account on this phone, and whether it is signed in (see lib/account). */
export function useAccount(): AccountControl {
  const [account, setAccount] = useState(() => fromStoredAccount(read(ACCOUNT_KEY)));
  const [session, setSession] = useState(() => read(SESSION_KEY));

  const signIn = (phone: string) => {
    write(SESSION_KEY, phone);
    setSession(phone);
  };

  return {
    account,
    signedIn: account !== null && session === account.phone,
    signUp: (name, phone, pin) => {
      const created = newAccount(name, phone, pin, newSalt());
      write(ACCOUNT_KEY, toStoredAccount(created));
      setAccount(created);
      signIn(created.phone);
    },
    logIn: (phone, pin) => {
      const result = logInResult(account, phone, pin);
      if (result === "ok" && account !== null) signIn(account.phone);
      return result;
    },
    signOut: () => {
      write(SESSION_KEY, null);
      setSession(null);
    },
  };
}
