import { useCallback, useState } from "react";
import { api } from "./api/endpoints";
import { ApprovalsPanel } from "./components/ApprovalsPanel";
import { BackendStatus } from "./components/BackendStatus";
import { CalendarPanel } from "./components/CalendarPanel";
import { ChatPanel } from "./components/ChatPanel";
import { ControlBar } from "./components/ControlBar";
import { InboxPanel } from "./components/InboxPanel";
import { SimulationPanel } from "./components/SimulationPanel";
import { TimelinePanel } from "./components/TimelinePanel";
import { ZonesPanel } from "./components/ZonesPanel";
import { useResource } from "./hooks/useResource";

export function App() {
  const [version, setVersion] = useState(0);
  const refresh = useCallback(() => setVersion((v) => v + 1), []);
  const plots = useResource(useCallback(() => api.plots(), []), version);
  const plot = plots.data?.[0];

  return (
    <main className="app">
      <div className="app__title">
        <h1>FieldPilot</h1>
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
      {plot ? (
        <>
          <ControlBar plot={plot} version={version} refresh={refresh} />
          <div className="layout">
            <div className="layout__main">
              <ApprovalsPanel plot={plot} version={version} refresh={refresh} />
              <ZonesPanel plot={plot} version={version} />
              <CalendarPanel plot={plot} version={version} refresh={refresh} />
              <TimelinePanel plot={plot} version={version} />
            </div>
            <aside className="layout__side">
              <ChatPanel plot={plot} refresh={refresh} />
              <SimulationPanel plot={plot} version={version} refresh={refresh} />
              <InboxPanel plot={plot} version={version} refresh={refresh} />
            </aside>
          </div>
        </>
      ) : null}
    </main>
  );
}
