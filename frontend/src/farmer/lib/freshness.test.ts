import { describe, expect, it } from "vitest";
import { ageText } from "./freshness";

const NOW = 1_000_000_000;
const MINUTE = 60_000;

describe("ageText", () => {
  it("calls anything under a minute just now", () => {
    expect(ageText(NOW, NOW)).toBe("just now");
    expect(ageText(NOW - 59_000, NOW)).toBe("just now");
  });

  it("counts whole minutes, then hours, then days", () => {
    expect(ageText(NOW - MINUTE, NOW)).toBe("1 min ago");
    expect(ageText(NOW - 59 * MINUTE, NOW)).toBe("59 min ago");
    expect(ageText(NOW - 60 * MINUTE, NOW)).toBe("1 h ago");
    expect(ageText(NOW - 25 * 60 * MINUTE, NOW)).toBe("1 day ago");
    expect(ageText(NOW - 72 * 60 * MINUTE, NOW)).toBe("3 days ago");
  });

  it("reads a time in the future as just now", () => {
    expect(ageText(NOW + 5 * MINUTE, NOW)).toBe("just now");
  });
});
