import { useCallback, useState } from "react";
import { api } from "../api/endpoints";
import { useAction } from "../hooks/useAction";
import { useResource } from "../hooks/useResource";
import { formatPlotTime } from "../lib/format";
import { ACTION_LABELS } from "../lib/labels";
import type { Plot, Task } from "../types/api";
import { Panel } from "./Panel";

interface ApprovalsPanelProps {
  plot: Plot;
  version: number;
  refresh: () => void;
}

/** Tasks the gate held for the farmer, with the reason in their words (D062, D067). */
export function ApprovalsPanel({ plot, version, refresh }: ApprovalsPanelProps) {
  const pending = useResource(useCallback(() => api.tasks("pending_approval"), []), version, 5_000);

  return (
    <Panel title="Pendientes de aprobación" error={pending.error}>
      {pending.data?.length === 0 ? <p className="muted">No hay nada esperando tu decisión.</p> : null}
      {pending.data?.map((task) => (
        <ApprovalCard key={task.id} task={task} plot={plot} refresh={refresh} />
      ))}
    </Panel>
  );
}

function ApprovalCard({ task, plot, refresh }: { task: Task; plot: Plot; refresh: () => void }) {
  const action = useAction(refresh);
  const [reason, setReason] = useState("");
  const volume = task.params.volume_mm;

  return (
    <article className="task-card task-card--pending">
      <h3>
        {ACTION_LABELS[task.action_type] ?? task.action_type}
        {typeof volume === "number" ? ` de ${volume} mm` : ""}
      </h3>
      <p className="muted">Programada para {formatPlotTime(task.scheduled_for, plot.utc_offset_hours)}</p>
      {task.reason_es ? <p className="task-card__reason">{task.reason_es}</p> : null}
      <p>{task.rationale}</p>
      <div className="button-row">
        <button className="button--primary" disabled={action.busy} onClick={() => action.run(() => api.approve(task.id))}>
          Aprobar
        </button>
        <input
          aria-label="Motivo del rechazo"
          placeholder="Motivo (opcional)"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
        />
        <button disabled={action.busy} onClick={() => action.run(() => api.reject(task.id, reason || undefined))}>
          Rechazar
        </button>
      </div>
      {action.error ? (
        <p className="panel__error" role="alert">
          {action.error}
        </p>
      ) : null}
    </article>
  );
}
