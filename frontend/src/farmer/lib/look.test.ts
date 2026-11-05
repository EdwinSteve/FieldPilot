import { describe, expect, it } from "vitest";
import { DEFAULT_LOOK, fromStoredLook, themeOf, toStoredLook } from "./look";

describe("the look saved on this phone", () => {
  it("round-trips the theme and the text size", () => {
    const look = { theme: "dark", text: "large" } as const;
    expect(fromStoredLook(toStoredLook(look))).toEqual(look);
  });

  it("starts from the phone's theme and normal text", () => {
    expect(fromStoredLook(null)).toEqual({ theme: "phone", text: "normal" });
    expect(DEFAULT_LOOK).toEqual({ theme: "phone", text: "normal" });
  });

  it("ignores what it cannot trust, one part at a time", () => {
    expect(fromStoredLook("not json")).toEqual(DEFAULT_LOOK);
    expect(fromStoredLook('{"version":2,"theme":"dark","text":"large"}')).toEqual(DEFAULT_LOOK);
    expect(fromStoredLook('{"version":1,"theme":"purple","text":"large"}')).toEqual({
      theme: "phone",
      text: "large",
    });
    expect(fromStoredLook('{"version":1,"theme":"light","text":3}')).toEqual({
      theme: "light",
      text: "normal",
    });
  });
});

describe("the theme on screen", () => {
  it("follows the phone only when the farmer left it to the phone", () => {
    expect(themeOf("phone", true)).toBe("dark");
    expect(themeOf("phone", false)).toBe("light");
    expect(themeOf("light", true)).toBe("light");
    expect(themeOf("dark", false)).toBe("dark");
  });
});
