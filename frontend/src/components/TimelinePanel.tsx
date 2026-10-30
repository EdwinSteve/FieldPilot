import { useCallback } from "react";
import { api } from "../api/endpoints";
import { useResource } from "../hooks/useResource";
import { formatPlotTime } from "../lib/format";
import { SUBAGENT_LABELS, groupRuns, type TimelineTurn } from "../lib/timeline";
import type { Json, Plot } from "../types/api";
import { Panel } from "./Panel";

const MAX_RUNS = 8;

interface TimelinePanelProps {
  plot: Plot;
  version: number;
}

/** What the agent did, run by run: plan (the tool and arguments), act, observe (D045). */
export function TimelinePanel({ plot, version }: TimelinePanelProps) {
  const events = useResource(
    useCallback(() => api.events({ kind: "agent_tool_call", limit: 400 }), []),
    version,
  );
  const runs = groupRuns(events.data ?? []).toReversed().slice(0, MAX_RUNS);

  return (
    <Panel title="Lo que hizo el agente" error={events.error} className="panel--wide">
      {runs.length === 0 ? <p className="muted">El agente todavía no ha trabajado.</p> : null}
      {runs.map((run) => (
        <details key={run.runId} className="timeline-run" open={runs[0]?.runId === run.runId}>
          <summary>
            <strong>{SUBAGENT_LABELS[run.subagent] ?? run.subagent}</strong> · {run.turns.length} turnos
            {run.refusals ? ` · ${run.refusals} rechazos de verificación` : ""}
            {run.paused ? " · en pausa: el modelo no respondió" : ""}
            {run.turns[0] ? ` · ${formatPlotTime(run.turns[0].occurredAt, plot.utc_offset_hours)}` : ""}
          </summary>
          <ol className="timeline-run__turns">
            {run.turns.map((turn) => (
              <TurnRow key={turn.eventId} turn={turn} />
            ))}
          </ol>
        </details>
      ))}
    </Panel>
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
      <span className="muted">{turn.durationMs} ms</span>
    </li>
  );
}

/** Short JSON for one line; the full value stays in the event log. */
function compact(value: Json): string {
  if (value === null) return "";
  const text = JSON.stringify(value);
  return text.length > 160 ? `${text.slice(0, 157)}…` : text;
}
