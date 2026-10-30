import { useCallback } from "react";
import { api } from "../api/endpoints";
import { useResource } from "../hooks/useResource";
import type { Clock, LogEvent, Plot } from "../types/api";
import { Panel } from "./Panel";
import { TaskCard } from "./TaskCard";

interface ApprovalsPanelProps {
  plot: Plot;
  version: number;
  clock: Clock | null;
  verdicts: Map<number, LogEvent>;
  refresh: () => void;
}

/** Tasks the gate held for the farmer, with the reason in their words (D062, D067). */
export function ApprovalsPanel({ plot, version, clock, verdicts, refresh }: ApprovalsPanelProps) {
  const pending = useResource(useCallback(() => api.tasks("pending_approval"), []), version);

  return (
    <Panel title="Pendientes de aprobación" error={pending.error} icon="shield">
      {pending.data?.length === 0 ? <p className="muted">No hay nada esperando tu decisión.</p> : null}
      {pending.data?.map((task) => (
        <TaskCard
          key={task.id}
          task={task}
          plot={plot}
          clock={clock}
          verdict={verdicts.get(task.id) ?? null}
          failure={null}
          refresh={refresh}
        />
      ))}
    </Panel>
  );
}
