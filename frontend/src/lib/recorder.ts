// Push-to-talk recording: the browser records, then we re-encode to the WAV the
// transcription service accepts (D061, D066). No library.
import { WAV_SAMPLE_RATE, encodeWav, resample } from "./wav";

export interface Recording {
  stop: () => Promise<Blob>;
}

/** Starts recording from the default microphone. `stop()` resolves to a mono 24 kHz WAV. */
export async function startRecording(): Promise<Recording> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const recorder = new MediaRecorder(stream);
  const chunks: Blob[] = [];
  recorder.addEventListener("dataavailable", (event) => chunks.push(event.data));
  recorder.start();

  return {
    stop: () =>
      new Promise<Blob>((resolve, reject) => {
        recorder.addEventListener("stop", () => {
          stream.getTracks().forEach((track) => track.stop());
          toWav(new Blob(chunks, { type: recorder.mimeType })).then(resolve, reject);
        });
        recorder.stop();
      }),
  };
}

async function toWav(recorded: Blob): Promise<Blob> {
  const context = new AudioContext();
  try {
    const decoded = await context.decodeAudioData(await recorded.arrayBuffer());
    const mono = resample(decoded.getChannelData(0), decoded.sampleRate, WAV_SAMPLE_RATE);
    return new Blob([encodeWav(mono, WAV_SAMPLE_RATE)], { type: "audio/wav" });
  } finally {
    await context.close();
  }
}
