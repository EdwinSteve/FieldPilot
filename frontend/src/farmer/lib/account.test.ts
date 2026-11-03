import { describe, expect, it } from "vitest";
import {
  fromStoredAccount,
  hashPin,
  logInResult,
  nameProblem,
  newAccount,
  normalPhone,
  phoneProblem,
  pinAgainProblem,
  pinProblem,
  toStoredAccount,
} from "./account";

const MARIA = newAccount(" María ", "+57 300-123 4567", "1234", "salt-1");

describe("phone numbers", () => {
  it("ignores spaces and dashes and keeps a leading +", () => {
    expect(normalPhone(" +57 300-123 4567 ")).toBe("+573001234567");
    expect(normalPhone("300 123 4567")).toBe("3001234567");
  });

  it("wants 8 to 15 digits", () => {
    expect(phoneProblem("123 4567")).toBe("phone_short");
    expect(phoneProblem("1234 5678")).toBeNull();
    expect(phoneProblem("+57 300 123 4567")).toBeNull();
    expect(phoneProblem("1234567890123456")).toBe("phone_long");
  });
});

describe("names and PINs", () => {
  it("needs a name", () => {
    expect(nameProblem("   ")).toBe("name_missing");
    expect(nameProblem("María")).toBeNull();
  });

  it("wants exactly four digits", () => {
    expect(pinProblem("1234")).toBeNull();
    expect(pinProblem("123")).toBe("pin_length");
    expect(pinProblem("12345")).toBe("pin_length");
    expect(pinProblem("12a4")).toBe("pin_length");
  });

  it("checks the second PIN only once the first is right", () => {
    expect(pinAgainProblem("1234", "1234")).toBeNull();
    expect(pinAgainProblem("1234", "4321")).toBe("pin_mismatch");
    expect(pinAgainProblem("12", "34")).toBeNull();
  });
});

describe("the PIN hash", () => {
  it("is the same for the same PIN and salt, and never the PIN itself", () => {
    expect(hashPin("1234", "salt-1")).toBe(hashPin("1234", "salt-1"));
    expect(hashPin("1234", "salt-1")).not.toContain("1234");
    expect(hashPin("1234", "salt-1")).toMatch(/^[0-9a-f]{8}$/);
  });

  it("changes with the PIN or the salt", () => {
    expect(hashPin("1234", "salt-1")).not.toBe(hashPin("1235", "salt-1"));
    expect(hashPin("1234", "salt-1")).not.toBe(hashPin("1234", "salt-2"));
  });
});

describe("logInResult", () => {
  it("signs in with the same phone and PIN, however the phone is typed", () => {
    expect(MARIA.name).toBe("María");
    expect(logInResult(MARIA, "+573001234567", "1234")).toBe("ok");
    expect(logInResult(MARIA, "+57 300 123 4567", "1234")).toBe("ok");
  });

  it("does not say which of the two was wrong", () => {
    expect(logInResult(MARIA, "+573001234567", "0000")).toBe("wrong");
    expect(logInResult(MARIA, "+573009999999", "1234")).toBe("wrong");
  });

  it("asks for an account when the phone has none", () => {
    expect(logInResult(null, "+573001234567", "1234")).toBe("no_account");
  });
});

describe("the stored account", () => {
  it("reads back what it saved", () => {
    expect(fromStoredAccount(toStoredAccount(MARIA))).toEqual(MARIA);
  });

  it("ignores what it cannot trust", () => {
    expect(fromStoredAccount(null)).toBeNull();
    expect(fromStoredAccount("not json")).toBeNull();
    expect(fromStoredAccount(JSON.stringify({ ...MARIA, version: 2 }))).toBeNull();
    expect(fromStoredAccount(JSON.stringify({ version: 1, name: "María" }))).toBeNull();
  });
});
