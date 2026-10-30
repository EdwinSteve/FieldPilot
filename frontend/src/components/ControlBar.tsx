import { useCallback } from "react";
import { api } from "../api/endpoints";
import { useAction } from "../hooks/useAction";
import { useResource } from "../hooks/useResource";
import { formatPlotTime } from "../lib/format";
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
  runCycle,
  refresh,
}: ControlBarProps) {
  const stop = useResource(useCallback(() => api.emergencyStop(), []), version);
  const action = useAction(refresh);
  const now = clock;
  const stopActive = stop.data?.active ?? false;

  return (
    <header className="control-bar">
      <div className="control-bar__clock">
        <span className="control-bar__label">
          <Icon name="clock" size={14} />
          Reloj simulado
        </span>
        <strong>{now ? formatPlotTime(now.now, plot.utc_offset_hours) : "…"}</strong>
        <span className="control-bar__speed">
          {now ? (now.paused ? "en pausa" : `×${now.speed_factor}`) : ""}
        </span>
        {autoTickOn ? (
          <output className="control-bar__autotick">Actualización automática cada 5 s</output>
        ) : null}
      </div>
      <div className="control-bar__buttons">
        {now?.paused ? (
          <button disabled={action.busy} onClick={() => action.run(() => api.changeClock({ action: "resume" }))}>
            Reanudar
          </button>
        ) : (
          <button disabled={action.busy} onClick={() => action.run(() => api.changeClock({ action: "pause" }))}>
            Pausar
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
          +1 día
        </button>
        <button disabled={action.busy} onClick={() => action.run(() => api.tick())}>
          Actualizar simulación
        </button>
        <button className="button--primary" disabled={action.busy} onClick={() => action.run(runCycle)}>
          Ejecutar ciclo diario
        </button>
        <button
          className={stopActive ? "button--stop button--stop-active" : "button--stop"}
          disabled={action.busy}
          onClick={() => action.run(() => api.setEmergencyStop(!stopActive))}
        >
          {stopActive ? "Desactivar parada de emergencia" : "Parada de emergencia"}
        </button>
      </div>
      {action.busy ? <p className="control-bar__status">Procesando…</p> : null}
      {action.error ?? tickError ? (
        <p className="panel__error" role="alert">
          {action.error ?? tickError}
        </p>
      ) : null}
      {stopActive ? (
        <output className="control-bar__stop">
          Parada de emergencia activa: ninguna acción que agregue agua se ejecuta.
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
