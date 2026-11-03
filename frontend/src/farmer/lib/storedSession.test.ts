import { describe, expect, it } from "vitest";
import { fromKnownFarmer, fromStoredSession, toKnownFarmer, toStoredSession } from "./storedSession";

const farmer = { id: 7, name: "Ana Pérez", phone: "+573001234567" };

describe("the stored session", () => {
  it("round-trips the refresh token and the farmer", () => {
    const session = { refreshToken: "Xq3", farmer };
    expect(fromStoredSession(toStoredSession(session))).toEqual(session);
  });

  it("never keeps an access token", () => {
    expect(toStoredSession({ refreshToken: "Xq3", farmer })).not.toContain("access");
  });

  it("ignores what it cannot trust", () => {
    expect(fromStoredSession(null)).toBeNull();
    expect(fromStoredSession("not json")).toBeNull();
    expect(fromStoredSession('{"version":2,"refreshToken":"x","farmer":{}}')).toBeNull();
    expect(fromStoredSession('{"version":1,"refreshToken":"x","farmer":{"id":"7"}}')).toBeNull();
  });
});

describe("the farmer known on this phone", () => {
  it("round-trips, with or without a home town", () => {
    const known = {
      name: "Ana",
      phone: "+573001234567",
      home: { department: "Huila", town: "La Plata" },
    };
    expect(fromKnownFarmer(toKnownFarmer(known))).toEqual(known);
    expect(fromKnownFarmer(toKnownFarmer({ ...known, home: null }))?.home).toBeNull();
  });

  it("ignores what it cannot trust, a typed city of version 1 included", () => {
    expect(fromKnownFarmer('{"version":2,"name":3}')).toBeNull();
    expect(fromKnownFarmer('{"version":1,"name":"Ana","phone":"+57300","city":"x"}')).toBeNull();
  });
});
