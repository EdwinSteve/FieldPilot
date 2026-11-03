import { useCallback, useState } from "react";
import { api } from "../api/endpoints";
import { fetchHealth } from "../api/health";
import { useAction } from "../hooks/useAction";
import { useResource } from "../hooks/useResource";
import { formatPlotTime } from "../lib/format";
import { dayAlreadyReplayed, isFixtureExhausted } from "../lib/mockMode";
import type { Clock, Plot } from "../types/api";
import { Icon } from "./icons";

const SPEEDS = [1, 60, 360];

interface ControlBarProps {
  plot: Plot;
  version: number;
  /** The shared clock read; the App owns the only interval (D071). */
  clock: Clock | null;
  autoTickOn: boolean;
  tickError: string | null;
  stopActive: boolean;
  /** Runs the cycle and remembers its result for the hero and the stepper. */
  runCycle: () => Promise<void>;
  refresh: () => void;
}

/** The simulated clock, the simulation tick, the daily cycle and the emergency stop. */
export function ControlBar({
  plot,
  version,
  clock,
  autoTickOn,
  tickError,
  stopActive,
  runCycle,
  refresh,
}: ControlBarProps) {
  const action = useAction(refresh);
  const health = useResource(useCallback(() => fetchHealth(), []), version);
  const reports = useResource(useCallback(() => api.reports(), []), version);
  const [exhausted, setExhausted] = useState(false);
  const now = clock;
  // Each recorded day replays once; a day that already ran is refused up front (D074, D076).
  const demoUsed =
    health.data?.mock_llm === true &&
    now !== null &&
    dayAlreadyReplayed(reports.data ?? [], now.now, plot.utc_offset_hours);

  // A mismatched farm still fails through useAction; the flag adds the way back.
  function runCycleOnce(): Promise<void> {
    return runCycle().then(
      () => setExhausted(false),
      (error: unknown) => {
        if (isFixtureExhausted(error)) setExhausted(true);
        throw error;
      },
    );
  }

  return (
    <header className="control-bar">
      <div className="control-bar__clock">
        <span className="control-bar__label">
          <Icon name="clock" size={14} />
          Simulated clock
        </span>
        <strong>{now ? formatPlotTime(now.now, plot.utc_offset_hours) : "…"}</strong>
        <span className="control-bar__speed">
          {now ? (now.paused ? "paused" : `×${now.speed_factor}`) : ""}
        </span>
        {autoTickOn ? (
          <output className="control-bar__autotick">Auto-refresh every 5 s</output>
        ) : null}
      </div>
      <div className="control-bar__buttons">
        {now?.paused ? (
          <button disabled={action.busy} onClick={() => action.run(() => api.changeClock({ action: "resume" }))}>
            Resume
          </button>
        ) : (
          <button disabled={action.busy} onClick={() => action.run(() => api.changeClock({ action: "pause" }))}>
            Pause
          </button>
        )}
        {SPEEDS.map((factor) => (
          <button
            key={factor}
            disabled={action.busy || now?.speed_factor === factor}
            onClick={() => action.run(() => api.changeClock({ action: "speed", speed_factor: factor }))}
          >
            ×{factor}
          </button>
        ))}
        <button disabled={action.busy} onClick={() => action.run(() => advanceAndTick(3_600))}>
          +1 h
        </button>
        <button disabled={action.busy} onClick={() => action.run(() => advanceAndTick(86_400))}>
          +1 day
        </button>
        <button disabled={action.busy} onClick={() => action.run(() => api.tick())}>
          Update simulation
        </button>
        <button
          className="button--primary"
          disabled={action.busy || demoUsed}
          onClick={() => action.run(runCycleOnce)}
        >
          Run daily cycle
        </button>
        <button
          className={stopActive ? "button--stop button--stop-active" : "button--stop"}
          disabled={action.busy}
          onClick={() => action.run(() => api.setEmergencyStop(!stopActive))}
        >
          {stopActive ? "Turn off emergency stop" : "Emergency stop"}
        </button>
      </div>
      {action.busy ? <p className="control-bar__status">Working…</p> : null}
      {action.error ?? tickError ? (
        <p className="panel__error" role="alert">
          {action.error ?? tickError}
        </p>
      ) : null}
      {demoUsed ? (
        <p className="notice">
          Today's recorded cycle already ran. Move to the next day with «+1 day», or
          reload the demo with <code>make seed</code> to repeat it.
        </p>
      ) : null}
      {exhausted && !demoUsed ? (
        <p className="notice">
          Reload the demo with <code>make seed</code> and run the cycle again.
        </p>
      ) : null}
      {stopActive ? (
        <output className="control-bar__stop">
          Emergency stop active: no action that adds water runs.
        </output>
      ) : null}
    </header>
  );
}

/** Moving the clock is followed by a tick, so readings and due tasks catch up (D065). */
async function advanceAndTick(seconds: number): Promise<void> {
  await api.changeClock({ action: "advance", advance_seconds: seconds });
  await api.tick();
}
