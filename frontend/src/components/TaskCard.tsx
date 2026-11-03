import { useState } from "react";
import { api } from "../api/endpoints";
import { useAction } from "../hooks/useAction";
import { formatPlotTime } from "../lib/format";
import { ACTION_LABELS, LEVEL_LABELS, RULE_LABELS, STATUS_LABELS } from "../lib/labels";
import { revertCard } from "../lib/revertCard";
import { parseVerdictInputs, type ParsedVerdict } from "../lib/verdict";
import type { Clock, LogEvent, Plot, Task } from "../types/api";

interface TaskCardProps {
  task: Task;
  plot: Plot;
  clock: Clock | null;
  /** The task's gate_verdict event, if the log has one. */
  verdict: LogEvent | null;
  /** The task's execution_failed event, if it failed. */
  failure: LogEvent | null;
  refresh: () => void;
}

/** One task as the demo tells it: the model proposes, the gate decides, the field shows it. */
export function TaskCard({ task, plot, clock, verdict, failure, refresh }: TaskCardProps) {
  const action = useAction(refresh);
  const [reason, setReason] = useState("");
  const volume = task.params.volume_mm;
  const parsed = verdict === null ? null : parseVerdictInputs(verdict.inputs);
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

      <div className="task-step">
        <span className="task-step__label">1 · The model proposed</span>
        <p className="task-card__rationale">{task.rationale}</p>
      </div>

      <div className="task-step">
        <span className="task-step__label">2 · The gate decided</span>
        {parsed === null ? <p className="muted">No verdict recorded.</p> : <VerdictFlow verdict={parsed} />}
      </div>

      <div className="task-step">
        <span className="task-step__label">3 · Outcome</span>
        <Outcome
          task={task}
          failureRule={failure?.rule ?? null}
          reason={reason}
          setReason={setReason}
          busy={action.busy}
          approve={() => action.run(() => api.approve(task.id))}
          reject={() => action.run(() => api.reject(task.id, reason || undefined))}
        />
        {card ? (
          <div className="revert-card">
            <span className="revert-card__label">{card.label}</span>
            <span>{card.status}</span>
            {card.estimate ? <span className="muted">{card.estimate}</span> : null}
            <button
              disabled={!card.buttonEnabled || action.busy}
              onClick={() => action.run(() => api.revert(task.id))}
            >
              Revert
            </button>
            {card.disabledReason ? <span className="muted">{card.disabledReason}</span> : null}
          </div>
        ) : null}
      </div>

      {action.error ? (
        <p className="panel__error" role="alert">
          {action.error}
        </p>
      ) : null}
    </article>
  );
}

function VerdictFlow({ verdict }: { verdict: ParsedVerdict }) {
  const tightened = verdict.requestedLevel !== verdict.effectiveLevel;
  return (
    <div className="verdict-flow">
      <span className="badge">{LEVEL_LABELS[verdict.requestedLevel] ?? verdict.requestedLevel}</span>
      {tightened ? (
        <>
          <span aria-hidden="true">→</span>
          <span className="badge badge--pending_approval">
            {LEVEL_LABELS[verdict.effectiveLevel] ?? verdict.effectiveLevel}
          </span>
        </>
      ) : null}
      {verdict.violations.length === 0 ? (
        <span className="muted">Within the limits: no rule fired.</span>
      ) : (
        <ul className="verdict-flow__rules">
          {verdict.violations.map((code) => (
            <li key={code}>{RULE_LABELS[code] ?? code}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

interface OutcomeProps {
  task: Task;
  failureRule: string | null;
  reason: string;
  setReason: (value: string) => void;
  busy: boolean;
  approve: () => void;
  reject: () => void;
}

function Outcome({ task, failureRule, reason, setReason, busy, approve, reject }: OutcomeProps) {
  if (task.status === "pending_approval") {
    return (
      <div>
        {task.reason ? <p className="task-card__reason">{task.reason}</p> : null}
        <div className="button-row">
          <button className="button--primary" disabled={busy} onClick={approve}>
            Approve
          </button>
          <input
            aria-label="Reason for rejecting"
            placeholder="Reason (optional)"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
          <button disabled={busy} onClick={reject}>
            Reject
          </button>
        </div>
      </div>
    );
  }
  if (task.status === "scheduled") return <p>On the calendar, waiting for its time.</p>;
  if (task.status === "executed") return <p>Completed.</p>;
  if (task.status === "rejected") return <p>The farmer rejected it.</p>;
  return <p>{failureRule ? `Not executed: ${RULE_LABELS[failureRule] ?? failureRule}.` : "Not executed."}</p>;
}
