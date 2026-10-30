import { useCallback } from "react";
import { api } from "../api/endpoints";
import { useResource } from "../hooks/useResource";
import { formatPlotTime } from "../lib/format";
import type { Clock, LogEvent, Plot, Task } from "../types/api";
import { Panel } from "./Panel";
import { TaskCard } from "./TaskCard";

interface CalendarPanelProps {
  plot: Plot;
  version: number;
  /** The shared clock read; the App owns the only interval (D071). */
  clock: Clock | null;
  verdicts: Map<number, LogEvent>;
  failures: Map<number, LogEvent>;
  refresh: () => void;
}

/** Every task by the plot's local day, newest day first, with the D011 revert card. */
export function CalendarPanel({ plot, version, clock, verdicts, failures, refresh }: CalendarPanelProps) {
  const tasks = useResource(useCallback(() => api.tasks(), []), version);
  const days = groupByDay(tasks.data ?? [], plot.utc_offset_hours);

  return (
    <Panel title="Calendario" error={tasks.error} icon="clock">
      {days.length === 0 ? <p className="muted">Todavía no hay tareas.</p> : null}
      {days.map(([day, dayTasks]) => (
        <div key={day} className="calendar-day">
          <h3>{day}</h3>
          {dayTasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              plot={plot}
              clock={clock}
              verdict={verdicts.get(task.id) ?? null}
              failure={failures.get(task.id) ?? null}
              refresh={refresh}
            />
          ))}
        </div>
      ))}
    </Panel>
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
