import { useCallback } from "react";
import { api } from "../api/endpoints";
import { useAction } from "../hooks/useAction";
import { useResource } from "../hooks/useResource";
import { formatPlotTime } from "../lib/format";
import { ACTION_LABELS, LEVEL_LABELS, STATUS_LABELS } from "../lib/labels";
import { revertCard } from "../lib/revertCard";
import type { Clock, Plot, Task } from "../types/api";
import { Panel } from "./Panel";

interface CalendarPanelProps {
  plot: Plot;
  version: number;
  /** The shared clock read; the App owns the only interval (D071). */
  clock: Clock | null;
  refresh: () => void;
}

/** Every task by the plot's local day, newest day first, with the D011 revert card. */
export function CalendarPanel({ plot, version, clock, refresh }: CalendarPanelProps) {
  const tasks = useResource(useCallback(() => api.tasks(), []), version);
  const days = groupByDay(tasks.data ?? [], plot.utc_offset_hours);

  return (
    <Panel title="Calendario" error={tasks.error}>
      {days.length === 0 ? <p className="muted">Todavía no hay tareas.</p> : null}
      {days.map(([day, dayTasks]) => (
        <div key={day} className="calendar-day">
          <h3>{day}</h3>
          {dayTasks.map((task) => (
            <CalendarTask key={task.id} task={task} plot={plot} clock={clock} refresh={refresh} />
          ))}
        </div>
      ))}
    </Panel>
  );
}

interface CalendarTaskProps {
  task: Task;
  plot: Plot;
  clock: Clock | null;
  refresh: () => void;
}

function CalendarTask({ task, plot, clock, refresh }: CalendarTaskProps) {
  const action = useAction(refresh);
  const volume = task.params.volume_mm;
  const card = revertCard({
    revertOpen: task.revert_open,
    remainingSeconds: task.revert_remaining_seconds,
    clockPaused: clock?.paused ?? true,
    speedFactor: clock?.speed_factor ?? 0,
  });

  return (
    <article className={`task-card task-card--${task.status}`}>
      <div className="task-card__head">
        <strong>
          {ACTION_LABELS[task.action_type] ?? task.action_type}
          {typeof volume === "number" ? ` ${volume} mm` : ""}
        </strong>
        <span className={`badge badge--${task.status}`}>{STATUS_LABELS[task.status] ?? task.status}</span>
        <span className="muted">
          {formatPlotTime(task.scheduled_for, plot.utc_offset_hours)} · {LEVEL_LABELS[task.effective_level]}
        </span>
      </div>
      <p className="task-card__rationale">{task.rationale}</p>
      {card ? (
        <div className="revert-card">
          <span className="revert-card__label">{card.label}</span>
          <span>{card.status}</span>
          {card.estimate ? <span className="muted">{card.estimate}</span> : null}
          <button disabled={!card.buttonEnabled || action.busy} onClick={() => action.run(() => api.revert(task.id))}>
            Revertir
          </button>
          {card.disabledReason ? <span className="muted">{card.disabledReason}</span> : null}
        </div>
      ) : null}
      {action.error ? (
        <p className="panel__error" role="alert">
          {action.error}
        </p>
      ) : null}
    </article>
  );
}

function groupByDay(tasks: readonly Task[], offsetHours: number): [string, Task[]][] {
  const days = new Map<string, Task[]>();
  const sorted = tasks.toSorted((a, b) => b.scheduled_for.localeCompare(a.scheduled_for));
  for (const task of sorted) {
    const day = formatPlotTime(task.scheduled_for, offsetHours).split(",")[0] ?? task.scheduled_for;
    days.set(day, [...(days.get(day) ?? []), task]);
  }
  return [...days.entries()];
}
