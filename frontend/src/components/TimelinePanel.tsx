import { useCallback, useMemo, useState } from "react";
import { api } from "../api/endpoints";
import { useResource } from "../hooks/useResource";
import { formatPlotTime } from "../lib/format";
import { EVENT_KIND_LABELS } from "../lib/labels";
import {
  SUBAGENT_LABELS,
  eventCategory,
  storyEntries,
  type StoryFilter,
  type TimelineRun,
  type TimelineTurn,
} from "../lib/timeline";
import type { Json, LogEvent, Plot } from "../types/api";
import { Icon, type IconName } from "./icons";
import { Panel } from "./Panel";

const MAX_ENTRIES = 30;

const FILTERS: { key: StoryFilter; label: string }[] = [
  { key: "all", label: "Todo" },
  { key: "agent", label: "Agente" },
  { key: "gate", label: "Gate y tareas" },
  { key: "system", label: "Sistema" },
];

const KIND_ICONS: Record<string, IconName> = {
  proposal: "leaf",
  gate_verdict: "shield",
  execution_requested: "valve",
  execution: "valve",
  execution_failed: "alert",
  revert: "clock",
  revert_refused: "alert",
  approval: "shield",
  rejection: "alert",
  notification: "alert",
  emergency_stop: "alert",
  stage_transition: "leaf",
  agent_tool_call: "mic",
  config_override: "shield",
  clock_changed: "clock",
  scenario_injected: "drop",
  phenology_gap: "satellite",
};

const SUBAGENT_ICONS: Record<string, IconName> = {
  monitoring: "drop",
  imaging: "satellite",
  irrigation: "valve",
  reporting: "leaf",
  orchestrator: "mic",
};

interface TimelinePanelProps {
  plot: Plot;
  version: number;
}

/** The event log as a story: agent runs opened into turns, everything else in line (D045). */
export function TimelinePanel({ plot, version }: TimelinePanelProps) {
  const events = useResource(useCallback(() => api.events({ limit: 500 }), []), version);
  const [filter, setFilter] = useState<StoryFilter>("all");
  const entries = useMemo(
    () => storyEntries(events.data ?? [], filter).slice(0, MAX_ENTRIES),
    [events.data, filter],
  );
  const counts = useMemo(() => {
    const all = storyEntries(events.data ?? [], "all");
    const runs = all.filter((e) => e.run !== null).length;
    const gate = all.filter((e) => e.event !== null && eventCategory(e.event.kind) === "gate").length;
    const system = all.filter(
      (e) => e.event !== null && eventCategory(e.event.kind) === "system",
    ).length;
    const agentSingles = all.filter(
      (e) => e.event !== null && eventCategory(e.event.kind) === "agent",
    ).length;
    return { all: all.length, agent: runs + agentSingles, gate, system };
  }, [events.data]);

  return (
    <Panel title="Libro de eventos" error={events.error} icon="clock" loading={events.loading}>
      <fieldset className="filter-group">
        <legend>Filtrar por tipo</legend>
        {FILTERS.map(({ key, label }) => (
          <button
            key={key}
            className={filter === key ? "button--primary" : undefined}
            aria-pressed={filter === key}
            onClick={() => setFilter(key)}
          >
            {label} ({counts[key]})
          </button>
        ))}
      </fieldset>
      {entries.length === 0 ? <p className="muted">Todavía no hay nada registrado.</p> : null}
      <ol className="story">
        {entries.map((entry) =>
          entry.run ? (
            <RunEntry key={entry.run.runId} run={entry.run} plot={plot} />
          ) : entry.event ? (
            <SingleEntry key={entry.event.id} event={entry.event} plot={plot} />
          ) : null,
        )}
      </ol>
    </Panel>
  );
}

function RunEntry({ run, plot }: { run: TimelineRun; plot: Plot }) {
  return (
    <li className="story-run">
      <div className="story-run__head">
        <Icon name={SUBAGENT_ICONS[run.subagent] ?? "leaf"} />
        <strong>{SUBAGENT_LABELS[run.subagent] ?? run.subagent}</strong>
        <span className="muted">· {run.turns.length} turnos</span>
        {run.refusals ? (
          <span className="badge badge--warn">{run.refusals} reintentos</span>
        ) : null}
        {run.paused ? <span className="badge badge--warn">en pausa</span> : null}
        {run.turns[0] ? (
          <span className="muted">· {formatPlotTime(run.turns[0].occurredAt, plot.utc_offset_hours)}</span>
        ) : null}
      </div>
      <ol className="story-run__turns">
        {run.turns.map((turn) => (
          <TurnRow key={turn.eventId} turn={turn} />
        ))}
      </ol>
    </li>
  );
}

function TurnRow({ turn }: { turn: TimelineTurn }) {
  if (turn.paused) {
    return <li className="turn turn--paused">Turno {turn.turn}: en pausa ({turn.error})</li>;
  }
  return (
    <li className={turn.error ? "turn turn--refused" : "turn"}>
      <span className="turn__plan">
        Turno {turn.turn}: {turn.tool ?? "respuesta de texto"} <code>{compact(turn.arguments)}</code>
      </span>
      <span className="turn__observe">
        {turn.error ? `Rechazado: ${turn.error}` : compact(turn.result)}
      </span>
      <details>
        <summary>ver detalle</summary>
        <code className="turn__detail">{JSON.stringify({ args: turn.arguments, result: turn.result }, null, 2)}</code>
      </details>
      <span className="muted">{turn.durationMs} ms</span>
    </li>
  );
}

function SingleEntry({ event, plot }: { event: LogEvent; plot: Plot }) {
  return (
    <li className="story-event">
      <Icon name={KIND_ICONS[event.kind] ?? "alert"} />
      <div>
        <div>
          <strong>{EVENT_KIND_LABELS[event.kind] ?? event.kind}</strong>{" "}
          <span className="muted">
            · {formatPlotTime(event.occurred_at, plot.utc_offset_hours)}
            {event.task_id === null ? "" : ` · tarea ${event.task_id}`}
          </span>
        </div>
        {event.reason ? <p className="story-event__reason">{event.reason}</p> : null}
      </div>
    </li>
  );
}

/** Short JSON for one line; the full value hides behind "ver detalle". */
function compact(value: Json): string {
  if (value === null) return "";
  const text = JSON.stringify(value);
  return text.length > 160 ? `${text.slice(0, 157)}…` : text;
}
