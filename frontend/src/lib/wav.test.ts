import { describe, expect, it } from "vitest";
import { encodeWav, resample } from "./wav";

function header(bytes: Uint8Array) {
  const view = new DataView(bytes.buffer);
  const ascii = (offset: number) => String.fromCharCode(...bytes.slice(offset, offset + 4));
  return {
    riff: ascii(0),
    wave: ascii(8),
    fmt: ascii(12),
    format: view.getUint16(20, true),
    channels: view.getUint16(22, true),
    rate: view.getUint32(24, true),
    byteRate: view.getUint32(28, true),
    bits: view.getUint16(34, true),
    data: ascii(36),
    dataBytes: view.getUint32(40, true),
    riffSize: view.getUint32(4, true),
  };
}

describe("encodeWav", () => {
  it("writes mono 16-bit PCM at the given rate, as the service requires", () => {
    const wav = encodeWav(new Float32Array(240), 24_000);

    expect(header(wav)).toEqual({
      riff: "RIFF",
      wave: "WAVE",
      fmt: "fmt ",
      format: 1,
      channels: 1,
      rate: 24_000,
      byteRate: 48_000,
      bits: 16,
      data: "data",
      dataBytes: 480,
      riffSize: 36 + 480,
    });
    expect(wav.length).toBe(44 + 480);
  });

  it("scales samples to 16-bit and clamps out-of-range values", () => {
    const wav = encodeWav(Float32Array.from([1, -1, 0, 2, -3, 0.5]), 16_000);
    const view = new DataView(wav.buffer);
    const sample = (i: number) => view.getInt16(44 + i * 2, true);

    expect([0, 1, 2, 3, 4].map(sample)).toEqual([32_767, -32_768, 0, 32_767, -32_768]);
    expect(sample(5)).toBe(16_383);
  });
});

describe("resample", () => {
  it("keeps the samples when the rate does not change", () => {
    const samples = Float32Array.from([0.1, 0.2]);

    expect(resample(samples, 24_000, 24_000)).toBe(samples);
  });

  it("changes the length in proportion to the rates", () => {
    expect(resample(new Float32Array(48_000), 48_000, 24_000).length).toBe(24_000);
    expect(resample(new Float32Array(441), 44_100, 24_000).length).toBe(240);
  });

  it("interpolates between neighbouring samples", () => {
    const out = resample(Float32Array.from([0, 1, 0, 1]), 2, 4);

    expect(Array.from(out.slice(0, 3))).toEqual([0, 0.5, 1]);
  });
});
