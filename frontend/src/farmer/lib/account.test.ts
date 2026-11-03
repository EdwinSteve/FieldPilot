import { describe, expect, it } from "vitest";
import {
  homeProblems,
  passwordMissing,
  colombianMobile,
  consentProblem,
  nameProblem,
  passwordAgainProblem,
  passwordProblem,
  phoneProblem,
} from "./account";

describe("colombianMobile", () => {
  it("reads a number however it is typed", () => {
    expect(colombianMobile("300 123-4567")).toBe("3001234567");
    expect(colombianMobile("+57 300 123 4567")).toBe("3001234567");
    expect(colombianMobile("573001234567")).toBe("3001234567");
  });

  it("refuses a landline, a short number or another country", () => {
    expect(colombianMobile("6012345678")).toBeNull();
    expect(colombianMobile("300123456")).toBeNull();
    expect(colombianMobile("+1 300 123 4567")).toBeNull();
  });
});

describe("the form rules", () => {
  it("wants a name of two letters or more", () => {
    expect(nameProblem(" A ")).toBe("name_short");
    expect(nameProblem("Ana")).toBeNull();
  });

  it("wants a Colombian mobile", () => {
    expect(phoneProblem("12345")).toBe("phone_invalid");
    expect(phoneProblem("310 987 6543")).toBeNull();
  });

  it("wants 10 to 128 characters, without the phone number", () => {
    expect(passwordProblem("cafe", "3001234567")).toBe("password_short");
    expect(passwordProblem("x".repeat(129), "3001234567")).toBe("password_long");
    expect(passwordProblem("mi3001234567", "300 123 4567")).toBe("password_has_phone");
    expect(passwordProblem("cafe-con-panela", "3001234567")).toBeNull();
  });

  it("checks the second password only once the first is fine", () => {
    expect(passwordAgainProblem("cafe", "other", "3001234567")).toBeNull();
    expect(passwordAgainProblem("cafe-con-panela", "cafe-con-pan", "3001234567")).toBe(
      "password_mismatch",
    );
    expect(passwordAgainProblem("cafe-con-panela", "cafe-con-panela", "3001234567")).toBeNull();
  });

  it("asks the log-in only for some password", () => {
    expect(passwordMissing("")).toBe("password_missing");
    expect(passwordMissing("x")).toBeNull();
  });

  it("wants a department, then a town, and the consent", () => {
    expect(homeProblems("", "")).toEqual({ department: "department_missing", town: null });
    expect(homeProblems("Huila", "")).toEqual({ department: null, town: "town_missing" });
    expect(homeProblems("Huila", "La Plata")).toEqual({ department: null, town: null });
    expect(consentProblem(false)).toBe("consent_missing");
    expect(consentProblem(true)).toBeNull();
  });
});
