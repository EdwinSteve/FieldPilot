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
  autonomous: "They run on their own and are recorded.",
  notify: "They run, you are told, and you can revert them.",
  approval: "They wait for your decision.",
};

/** What the gate may do on its own, what it announces, and what waits for the farmer. */
export function AutonomyLegend({ version, stopActive }: AutonomyLegendProps) {
  const policy = useResource(useCallback(() => api.policy(), []), version);
  const groups = groupByLevel(policy.data?.defaults ?? {});
  const always = (policy.data?.always_approval ?? []).map((a) => ACTION_LABELS[a] ?? a);

  return (
    <Panel title="Autonomy: who decides" error={policy.error} icon="shield" loading={policy.loading}>
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
      {always.length > 0 ? <p>Always with approval: {always.join(", ")}.</p> : null}
      <p className="muted">At some stages the crop may ask for more control.</p>
      <p>
        Emergency stop:{" "}
        {stopActive ? (
          <strong>active: no action that adds water runs.</strong>
        ) : (
          "inactiva."
        )}
      </p>
    </Panel>
  );
}
