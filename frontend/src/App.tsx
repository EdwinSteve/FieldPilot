import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api/endpoints";
import { ApprovalsPanel } from "./components/ApprovalsPanel";
import { BackendStatus } from "./components/BackendStatus";
import { CalendarPanel } from "./components/CalendarPanel";
import { ChatPanel } from "./components/ChatPanel";
import { ControlBar } from "./components/ControlBar";
import { AutonomyLegend } from "./components/AutonomyLegend";
import { CycleStepper } from "./components/CycleStepper";
import { HeroDiagram } from "./components/HeroDiagram";
import { Icon } from "./components/icons";
import { InboxPanel } from "./components/InboxPanel";
import { SatellitePanel } from "./components/SatellitePanel";
import { SimulationPanel } from "./components/SimulationPanel";
import { StageBar } from "./components/StageBar";
import { TimelinePanel } from "./components/TimelinePanel";
import { ZonesPanel } from "./components/ZonesPanel";
import { describeError, useResource } from "./hooks/useResource";
import { isTickDue, shouldAutoTick } from "./lib/autoTick";
import { eventsByTask } from "./lib/verdict";
import type { DailyCycleResult } from "./types/api";

/** The single refresh cadence of the app: one interval bumps `version` (D071). */
const REFRESH_MS = 3_000;

export function App() {
  const [version, setVersion] = useState(0);
  const refresh = useCallback(() => setVersion((v) => v + 1), []);
  const plots = useResource(useCallback(() => api.plots(), []), version);
  const plot = plots.data?.[0];
  // The one clock read of the app; every panel that needs it gets this (D071).
  const clock = useResource(useCallback(() => api.clock(), []), version);
  const stop = useResource(useCallback(() => api.emergencyStop(), []), version);
  const stopActive = stop.data?.active ?? false;
  // The gate's paper trail, read once and joined onto tasks by the panels.
  const verdictEvents = useResource(
    useCallback(() => api.events({ kind: "gate_verdict", limit: 500 }), []),
    version,
  );
  const failedEvents = useResource(
    useCallback(() => api.events({ kind: "execution_failed", limit: 200 }), []),
    version,
  );
  const verdicts = useMemo(() => eventsByTask(verdictEvents.data ?? []), [verdictEvents.data]);
  const failures = useMemo(() => eventsByTask(failedEvents.data ?? []), [failedEvents.data]);
  const [tickError, setTickError] = useState<string | null>(null);
  const [lastCycle, setLastCycle] = useState<DailyCycleResult | null>(null);
  const [cycleRunning, setCycleRunning] = useState(false);

  const tick = useCallback(() => {
    api
      .tick()
      .then(() => {
        setTickError(null);
        refresh();
      })
      .catch((error: unknown) => setTickError(describeError(error)));
  }, [refresh]);

  const paused = clock.data?.paused ?? true;
  useDashboardLoop(paused, refresh, tick);
  const autoTickOn = clock.data !== null && !paused;

  const plotId = plot?.id;
  const runCycle = useCallback(async () => {
    if (plotId === undefined) return;
    setCycleRunning(true);
    try {
      setLastCycle(await api.dailyCycle(plotId));
    } finally {
      setCycleRunning(false);
    }
  }, [plotId]);

  return (
    <main className="app">
      <div className="app__title">
        <h1>
          <Icon name="leaf" size={26} />
          FieldPilot
        </h1>
        <span className="muted">{plot ? `${plot.name} · ${plot.area_ha} ha` : ""}</span>
        <BackendStatus />
      </div>
      {plots.error ? (
        <p className="panel__error" role="alert">
          {plots.error}
        </p>
      ) : null}
      {plots.data && !plot ? (
        <p className="notice">No hay ninguna parcela todavía. Carga la granja de demostración con `make seed`.</p>
      ) : null}
      <HeroDiagram lastCycle={lastCycle} />
      {plot ? (
        <>
          <ControlBar
            plot={plot}
            clock={clock.data}
            autoTickOn={autoTickOn}
            tickError={tickError}
            stopActive={stopActive}
            runCycle={runCycle}
            refresh={refresh}
          />
          <CycleStepper
            plotId={plot.id}
            version={version}
            running={cycleRunning}
            lastCycle={lastCycle}
          />
          <div className="layout">
            <div className="layout__main">
              <ApprovalsPanel
                plot={plot}
                version={version}
                clock={clock.data}
                verdicts={verdicts}
                refresh={refresh}
              />
              <ZonesPanel plot={plot} version={version} />
              <SatellitePanel plot={plot} version={version} />
              <StageBar plot={plot} version={version} clock={clock.data} />
              <CalendarPanel
                plot={plot}
                version={version}
                clock={clock.data}
                verdicts={verdicts}
                failures={failures}
                refresh={refresh}
              />
              <TimelinePanel plot={plot} version={version} />
            </div>
            <aside className="layout__side">
              <ChatPanel plot={plot} version={version} refresh={refresh} />
              <SimulationPanel
                plot={plot}
                version={version}
                clock={clock.data}
                refresh={refresh}
              />
              <InboxPanel plot={plot} version={version} refresh={refresh} />
              <AutonomyLegend version={version} stopActive={stopActive} />
            </aside>
          </div>
        </>
      ) : null}
    </main>
  );
}

/**
 * The only interval in the app (D071). Every REFRESH_MS it refreshes every
 * panel through `version`, and ticks the simulation when one is due. Nothing
 * happens while the tab is hidden; a tick also needs the clock running (D070).
 */
function useDashboardLoop(clockPaused: boolean, refresh: () => void, tick: () => void): void {
  const latest = useRef({ clockPaused, refresh, tick });
  useEffect(() => {
    latest.current = { clockPaused, refresh, tick };
  }, [clockPaused, refresh, tick]);

  const lastTick = useRef(0);
  useEffect(() => {
    const timer = window.setInterval(() => {
      const hidden = document.visibilityState === "hidden";
      const { clockPaused: paused, refresh: reload, tick: run } = latest.current;
      if (!hidden) reload();
      if (shouldAutoTick(paused, hidden) && isTickDue(lastTick.current, Date.now())) {
        lastTick.current = Date.now();
        run();
      }
    }, REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);
}
