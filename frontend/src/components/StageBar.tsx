import { useCallback } from "react";
import { api } from "../api/endpoints";
import { useResource } from "../hooks/useResource";
import { formatDayMonth, formatNumber } from "../lib/format";
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
  const cycle = cycles.data?.find((c) => c.status === "active") ?? cycles.data?.[0] ?? null;
  const cropName = cycle?.crop ?? null;
  // The crop's stages come from its catalogue entry, so any crop draws its own bar (D077).
  const crop = useResource(
    useCallback(() => (cropName === null ? Promise.resolve(null) : api.crop(cropName)), [cropName]),
    version,
  );
  const order = crop.data?.stages.map((stage) => stage.name) ?? [];
  const labels = new Map(crop.data?.stages.map((stage) => [stage.name, stage.display_es]) ?? []);
  const steps = stageProgress(order, cycle?.stages ?? []);
  const days =
    cycle === null || clock === null
      ? null
      : daysSinceSowing(cycle.sowing_date, clock.now, plot.utc_offset_hours);

  const cropLabel = cycle === null ? "—" : (crop.data?.display_es ?? cycle.crop);
  return (
    <Panel
      title={`Cultivo: ${cropLabel}`}
      error={cycles.error ?? crop.error}
      icon="leaf"
      loading={cycles.loading}
    >
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
                  <span className="stepper-node__label">{labels.get(step.name) ?? step.name}</span>
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
