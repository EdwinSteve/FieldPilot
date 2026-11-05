import { describe, expect, it } from "vitest";
import { canRunWarehouse, canShop, fromStoredUser, toStoredUser } from "./storedUser";

const user = { id: 6, name: "Laura", phone: "+573245865329", role: "customer" } as const;

describe("the stored marketplace login", () => {
  it("round-trips the refresh token and the user", () => {
    const stored = { refreshToken: "Xq3", user };
    expect(fromStoredUser(toStoredUser(stored))).toEqual(stored);
  });

  it("never keeps an access token", () => {
    expect(toStoredUser({ refreshToken: "Xq3", user })).not.toContain("access");
  });

  it("ignores what it cannot trust", () => {
    expect(fromStoredUser(null)).toBeNull();
    expect(fromStoredUser("nope")).toBeNull();
    expect(fromStoredUser('{"version":2,"refreshToken":"x","user":{}}')).toBeNull();
    expect(fromStoredUser('{"version":1,"refreshToken":"x","user":{"id":1,"name":"A","phone":"+57","role":"king"}}')).toBeNull();
  });
});

describe("what each role does here", () => {
  it("lets customers shop and operators and admins run the warehouse", () => {
    expect(canShop("customer")).toBe(true);
    expect(canShop("operator")).toBe(false);
    expect(canRunWarehouse("operator")).toBe(true);
    expect(canRunWarehouse("admin")).toBe(true);
    expect(canRunWarehouse("customer")).toBe(false);
    expect(canRunWarehouse(null)).toBe(false);
  });
});
