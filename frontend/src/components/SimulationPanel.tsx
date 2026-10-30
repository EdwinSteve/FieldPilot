import { useCallback } from "react";
import { api } from "../api/endpoints";
import { useAction } from "../hooks/useAction";
import { useResource } from "../hooks/useResource";
import { formatPlotTime } from "../lib/format";
import type { Clock, Json, Plot, ScenarioRequest } from "../types/api";
import { Panel } from "./Panel";

const NAMES: Record<string, string> = { drought: "sequía", heavy_rain: "lluvia fuerte" };

interface SimulationPanelProps {
  plot: Plot;
  version: number;
  /** The shared clock read; the App owns the only interval (D071). */
  clock: Clock | null;
  refresh: () => void;
}

/** Scenarios come from the simulator only; a restart that dropped one is said plainly (D014). */
export function SimulationPanel({ plot, version, clock, refresh }: SimulationPanelProps) {
  const status = useResource(useCallback(() => api.simulationStatus(), []), version);
  const action = useAction(refresh);
  const now = clock?.now;

  function inject(name: ScenarioRequest["name"], hours: number) {
    if (!now) return;
    const end = new Date(Date.parse(now) + hours * 3_600_000).toISOString();
    return action.run(() => api.injectScenario({ name, start: now, end }));
  }

  const describe = (scenario: Record<string, Json>) => {
    const name = NAMES[String(scenario.name)] ?? String(scenario.name);
    const end = typeof scenario.end === "string" ? formatPlotTime(scenario.end, plot.utc_offset_hours) : "";
    return `${name}, hasta ${end}`;
  };

  return (
    <Panel title="Simulación" error={status.error ?? action.error}>
      {status.data?.lost.map((scenario) => (
        <output key={`${String(scenario.name)}-${String(scenario.start)}`} className="notice">
          El simulador se reinició; el escenario «{NAMES[String(scenario.name)] ?? String(scenario.name)}» ya
          no se está aplicando.
        </output>
      ))}
      <p>
        <strong>Activo ahora:</strong>{" "}
        {status.data?.active.length ? status.data.active.map(describe).join("; ") : "ninguno"}
      </p>
      {status.data?.upcoming.length ? (
        <p>
          <strong>Próximo:</strong> {status.data.upcoming.map(describe).join("; ")}
        </p>
      ) : null}
      <div className="button-row">
        <button disabled={action.busy || !now} onClick={() => inject("drought", 48)}>
          Inyectar sequía (48 h)
        </button>
        <button disabled={action.busy || !now} onClick={() => inject("heavy_rain", 6)}>
          Inyectar lluvia fuerte (6 h)
        </button>
      </div>
    </Panel>
  );
}
