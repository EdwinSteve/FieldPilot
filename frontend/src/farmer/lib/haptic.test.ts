import { describe, expect, it, vi } from "vitest";
import { buzz } from "./haptic";

describe("buzz", () => {
  it("vibrates briefly where the phone can", () => {
    const vibrate = vi.fn<(pattern: number) => boolean>(() => true);
    buzz({ vibrate });
    expect(vibrate).toHaveBeenCalledWith(20);
  });

  it("does nothing where it cannot", () => {
    expect(() => buzz({})).not.toThrow();
    expect(() =>
      buzz({
        vibrate: () => {
          throw new Error("blocked");
        },
      }),
    ).not.toThrow();
  });
});
