import { describe, expect, it } from "vitest";
import { CLOSED_TEXT, PAUSED_TEXT, WINDOW_LABEL, realEstimate, revertCard } from "./revertCard";

const OPEN = { revertOpen: true, remainingSeconds: 18_720, clockPaused: false, speedFactor: 360 };

describe("revertCard (D011)", () => {
  it("is labelled as a simulated-clock window, with the simulated time left", () => {
    const card = revertCard(OPEN);

    expect(card?.label).toBe(WINDOW_LABEL);
    expect(card?.label).toBe("Ventana en reloj simulado");
    expect(card?.status).toBe("Quedan 5 h 12 min de reloj simulado");
    expect(card?.buttonEnabled).toBe(true);
  });

  it("marks the real-time figure as an estimate", () => {
    expect(revertCard(OPEN)?.estimate).toBe("≈ 52 s reales a ×360 (estimación)");
  });

  it("says the window does not advance while the clock is paused, and shows no estimate", () => {
    const card = revertCard({ ...OPEN, clockPaused: true });

    expect(card?.status).toBe(`Quedan 5 h 12 min de reloj simulado. ${PAUSED_TEXT}`);
    expect(PAUSED_TEXT).toBe("Reloj simulado en pausa: la ventana no avanza");
    expect(card?.estimate).toBeNull();
    expect(card?.buttonEnabled).toBe(true);
  });

  it("disables the button with the reason visible once the backend closes it", () => {
    const card = revertCard({ ...OPEN, revertOpen: false, remainingSeconds: 0 });

    expect(card?.status).toBe(CLOSED_TEXT);
    expect(card?.buttonEnabled).toBe(false);
    expect(card?.disabledReason).toBe("Ventana cerrada");
    expect(card?.estimate).toBeNull();
  });

  it("follows revert_open even when time seems left: the UI never computes expiry", () => {
    const card = revertCard({ ...OPEN, revertOpen: false, remainingSeconds: 600 });

    expect(card?.buttonEnabled).toBe(false);
  });

  it("follows revert_open even when no time seems left", () => {
    const card = revertCard({ ...OPEN, remainingSeconds: 0 });

    expect(card?.buttonEnabled).toBe(true);
  });

  it("is absent for a task that never had a window", () => {
    expect(revertCard({ ...OPEN, revertOpen: null })).toBeNull();
  });
});

describe("realEstimate", () => {
  it("is null without a positive speed", () => {
    expect(realEstimate(600, 0)).toBeNull();
  });

  it("divides by the speed factor", () => {
    expect(realEstimate(3_600, 60)).toBe("≈ 1 min reales a ×60 (estimación)");
  });
});
