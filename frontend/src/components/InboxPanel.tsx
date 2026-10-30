import { useCallback } from "react";
import { api } from "../api/endpoints";
import { useAction } from "../hooks/useAction";
import { useResource } from "../hooks/useResource";
import { formatPlotTime } from "../lib/format";
import type { Plot } from "../types/api";
import { Panel } from "./Panel";

interface InboxPanelProps {
  plot: Plot;
  version: number;
  refresh: () => void;
}

/** What the farmer was told: notifications, and the verified daily reports. */
export function InboxPanel({ plot, version, refresh }: InboxPanelProps) {
  const notes = useResource(useCallback(() => api.notifications(), []), version);
  const reports = useResource(useCallback(() => api.reports(), []), version);
  const action = useAction(refresh);
  const time = (iso: string) => formatPlotTime(iso, plot.utc_offset_hours);

  return (
    <>
      <Panel title="Avisos" error={notes.error ?? action.error} icon="alert">
        {notes.data?.length === 0 ? <p className="muted">Sin avisos.</p> : null}
        <ul className="inbox">
          {notes.data?.toReversed().map((note) => (
            <li key={note.id} className={note.read_at ? "inbox__item" : "inbox__item inbox__item--unread"}>
              <span className="muted">{time(note.created_at)}</span> {note.message}
              {note.read_at ? null : (
                <button disabled={action.busy} onClick={() => action.run(() => api.markRead(note.id))}>
                  Marcar como leído
                </button>
              )}
            </li>
          ))}
        </ul>
      </Panel>
      <Panel title="Informes del día" error={reports.error} icon="leaf">
        {reports.data?.length === 0 ? <p className="muted">Todavía no hay informes.</p> : null}
        {reports.data?.toReversed().map((report) => (
          <article key={report.id} className="report">
            <span className="muted">{time(report.created_at)}</span>
            <p>{report.content}</p>
          </article>
        ))}
      </Panel>
    </>
  );
}
