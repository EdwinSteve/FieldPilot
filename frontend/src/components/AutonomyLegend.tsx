import { useCallback } from "react";
import { api } from "../api/endpoints";
import { useResource } from "../hooks/useResource";
import { ACTION_LABELS, LEVEL_LABELS } from "../lib/labels";
import { groupByLevel } from "../lib/policy";
import { Panel } from "./Panel";

interface AutonomyLegendProps {
  version: number;
  stopActive: boolean;
}

const LEVEL_DESCRIPTIONS: Record<string, string> = {
  autonomous: "Se ejecutan solas y quedan registradas.",
  notify: "Se ejecutan, te avisan y se pueden revertir.",
  approval: "Esperan tu decisión.",
};

/** What the gate may do on its own, what it announces, and what waits for the farmer. */
export function AutonomyLegend({ version, stopActive }: AutonomyLegendProps) {
  const policy = useResource(useCallback(() => api.policy(), []), version);
  const groups = groupByLevel(policy.data?.defaults ?? {});
  const always = (policy.data?.always_approval ?? []).map((a) => ACTION_LABELS[a] ?? a);

  return (
    <Panel title="Autonomía: quién decide" error={policy.error} icon="shield">
      {(["autonomous", "notify", "approval"] as const).map((level) => (
        <div key={level} className="legend-block">
          <span className="badge">{LEVEL_LABELS[level]}</span>
          <p className="muted">{LEVEL_DESCRIPTIONS[level]}</p>
          <ul className="chip-list">
            {groups[level].map((action) => (
              <li key={action} className="chip">
                {ACTION_LABELS[action] ?? action}
              </li>
            ))}
          </ul>
        </div>
      ))}
      {always.length > 0 ? <p>Siempre con aprobación: {always.join(", ")}.</p> : null}
      <p className="muted">En alguna etapa el cultivo puede pedir más control.</p>
      <p>
        Parada de emergencia:{" "}
        {stopActive ? (
          <strong>activa, ninguna acción que agregue agua se ejecuta.</strong>
        ) : (
          "inactiva."
        )}
      </p>
    </Panel>
  );
}
