import { useCallback } from "react";
import { api } from "../api/endpoints";
import { useResource } from "../hooks/useResource";
import { formatDayMonth, formatNumber } from "../lib/format";
import { CROP_LABELS, STAGE_LABELS } from "../lib/labels";
import { daysSinceSowing, stageProgress } from "../lib/stages";
import type { Clock, Plot } from "../types/api";
import { Panel } from "./Panel";

interface StageBarProps {
  plot: Plot;
  version: number;
  clock: Clock | null;
}

/** Where the crop stands: its stages, accumulated heat and days since sowing. */
export function StageBar({ plot, version, clock }: StageBarProps) {
  const cycles = useResource(useCallback(() => api.cycles(), []), version);
  const cycle = cycles.data?.find((c) => c.status === "growing") ?? cycles.data?.[0] ?? null;
  const steps = stageProgress(cycle?.stages ?? []);
  const days =
    cycle === null || clock === null
      ? null
      : daysSinceSowing(cycle.sowing_date, clock.now, plot.utc_offset_hours);

  const crop = cycle === null ? "—" : (CROP_LABELS[cycle.crop] ?? cycle.crop);
  return (
    <Panel title={`Cultivo: ${crop}`} error={cycles.error} icon="leaf" loading={cycles.loading}>
      {cycle === null ? <p className="muted">Todavía no hay un cultivo en esta parcela.</p> : null}
      {cycle === null ? null : (
        <>
          <ol className="stepper">
            {steps.map((step, i) => (
              <li key={step.name} className="stepper__item">
                <span
                  className={`stepper-node stepper-node--${step.state}`}
                  aria-current={step.state === "current" ? "step" : undefined}
                >
                  <span className="stepper-node__label">{STAGE_LABELS[step.name] ?? step.name}</span>
                </span>
                {i < steps.length - 1 ? <span className="stepper__link" aria-hidden="true" /> : null}
              </li>
            ))}
          </ol>
          <p>
            Acumulados: <strong>{formatNumber(cycle.accumulated_gdd, 0)} GDD</strong>
            {days === null ? "" : (
              <>
                {" "}· {days} días desde la siembra ({formatDayMonth(cycle.sowing_date)})
              </>
            )}
          </p>
        </>
      )}
    </Panel>
  );
}
