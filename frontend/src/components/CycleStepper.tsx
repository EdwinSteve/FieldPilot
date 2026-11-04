import { useCallback } from "react";
import { api } from "../api/endpoints";
import { useResource } from "../hooks/useResource";
import { parseBrief } from "../lib/brief";
import {
  CYCLE_STEPS,
  contextStates,
  stepStates,
  stepTurns,
  type ContextState,
  type CycleStep,
  type StepState,
} from "../lib/cycle";
import { formatNumber } from "../lib/format";
import { ACTION_LABELS, LEVEL_LABELS, OUTCOME_LABELS, ZONE_STATUS_LABELS } from "../lib/labels";
import { SUBAGENT_LABELS } from "../lib/timeline";
import type { DailyCycleResult } from "../types/api";
import { Panel } from "./Panel";

interface CycleStepperProps {
  plotId: number;
  version: number;
  running: boolean;
  lastCycle: DailyCycleResult | null;
}

const OUTCOME_BADGES: Record<string, string> = {
  execute: "badge--executed",
  execute_notify: "badge--scheduled",
  await_approval: "badge--pending_approval",
};

/** "fungal_disease" -> "fungal disease", "ph_low" -> "low pH". */
function humanize(code: string): string {
  if (code === "ph_low") return "low pH";
  if (code === "ph_high") return "high pH";
  return code.replaceAll("_", " ");
}

/** The daily cycle as nodes (the agronomist and its specialists), and what it found. */
export function CycleStepper({ plotId, version, running, lastCycle }: CycleStepperProps) {
  const zones = useResource(useCallback(() => api.zones(plotId), [plotId]), version);
  const nameOf = (zoneId: number) => zones.data?.find((z) => z.id === zoneId)?.name ?? `Zone ${zoneId}`;
  const states = stepStates(lastCycle);
  const turns = stepTurns(lastCycle);
  const context = contextStates(lastCycle);
  const brief = lastCycle === null ? null : parseBrief(lastCycle.brief);

  const nodes: { key: string; label: string; caption: string; state: StepState | ContextState }[] = [
    { key: "sources", label: "Sensors and satellite", caption: "", state: context.sources },
    ...CYCLE_STEPS.map((step: CycleStep) => ({
      key: step,
      label: SUBAGENT_LABELS[step] ?? step,
      caption: captionFor(states[step], turns[step]),
      state: states[step],
    })),
    { key: "gate", label: "Gate", caption: "", state: context.gate },
  ];

  return (
    <Panel title="Daily cycle" icon="leaf">
      <ol className={`stepper ${running ? "stepper--running" : ""}`}>
        {nodes.map((node, i) => (
          <li key={node.key} className="stepper__item" style={{ animationDelay: `${i * 0.15}s` }}>
            <span className={`stepper-node stepper-node--${node.state}`}>
              <span className="stepper-node__number" aria-hidden="true">
                {i + 1}
              </span>
              <span className="stepper-node__label">{node.label}</span>
              {node.caption ? <span className="muted">{node.caption}</span> : null}
            </span>
            {i < nodes.length - 1 ? <span className="stepper__link" aria-hidden="true" /> : null}
          </li>
        ))}
      </ol>
      {running ? (
        <output className="muted">The agent is walking the plot…</output>
      ) : null}
      {brief === null && !running ? (
        <p className="muted">No cycle today yet. Press «Run daily cycle».</p>
      ) : null}
      {brief === null ? null : (
        <div className="brief-grid">
          <div className="brief-block">
            <h3>Zone readings</h3>
            {brief.zones.length === 0 ? <p className="muted">No reading.</p> : null}
            <ul>
              {brief.zones.map((zone) => (
                <li key={zone.zoneId}>
                  <strong>{nameOf(zone.zoneId)}</strong>: {ZONE_STATUS_LABELS[zone.status] ?? zone.status}
                  {zone.moisturePct === null ? "" : ` · moisture ${formatNumber(zone.moisturePct)} %`}
                </li>
              ))}
            </ul>
          </div>
          <div className="brief-block">
            <h3>Imagery</h3>
            {brief.imaging.length === 0 ? <p className="muted">No image for this day.</p> : null}
            <ul>
              {brief.imaging.map((zone) => (
                <li key={zone.zoneId}>
                  <strong>{nameOf(zone.zoneId)}</strong>: NDVI{" "}
                  {zone.ndviMean === null ? "unknown" : formatNumber(zone.ndviMean, 3)}
                  {zone.lowVigor ? " · low vigour" : ""} · bare soil{" "}
                  {zone.bareSoilPct === null
                    ? "unknown"
                    : `about ${formatNumber(zone.bareSoilPct, 0)} %`}
                </li>
              ))}
            </ul>
          </div>
          {brief.health.length + brief.nutrition.length > 0 ? (
            <div className="brief-block">
              <h3>Crop health and soil</h3>
              <ul>
                {brief.health.map((zone) => (
                  <li key={`h${zone.zoneId}`}>
                    <strong>{nameOf(zone.zoneId)}</strong>: {zone.level} risk
                    {zone.items.length ? ` · ${zone.items.map(humanize).join(", ")}` : ""}
                  </li>
                ))}
                {brief.nutrition.map((zone) => (
                  <li key={`n${zone.zoneId}`}>
                    <strong>{nameOf(zone.zoneId)}</strong>: soil {zone.level}
                    {zone.items.length ? ` · short of ${zone.items.map(humanize).join(", ")}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          <div className="brief-block">
            <h3>Proposals and gate</h3>
            {brief.proposals.length === 0 ? <p className="muted">No proposals in this cycle.</p> : null}
            <ul>
              {brief.proposals.map((proposal) => (
                <li key={proposal.taskId}>
                  {ACTION_LABELS[proposal.actionType] ?? proposal.actionType}
                  {proposal.zoneId === null ? "" : ` · ${nameOf(proposal.zoneId)}`} ·{" "}
                  <span className={`badge ${OUTCOME_BADGES[proposal.outcome] ?? ""}`}>
                    {OUTCOME_LABELS[proposal.outcome] ?? proposal.outcome}
                  </span>{" "}
                  <span className="muted">{LEVEL_LABELS[proposal.level] ?? proposal.level}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </Panel>
  );
}

function captionFor(state: StepState, turns: number | null): string {
  if (turns === null) return "";
  if (state === "stopped") return `${turns} turns · stopped`;
  return `${turns} turns`;
}
