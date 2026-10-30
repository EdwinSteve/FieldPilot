import { useCallback } from "react";
import { api } from "../api/endpoints";
import { useResource } from "../hooks/useResource";
import { formatNumber } from "../lib/format";
import type { Plot, SensorReadings, Zone, ZoneImagery } from "../types/api";
import { Panel } from "./Panel";

interface ZonesPanelProps {
  plot: Plot;
  version: number;
}

/** Each zone: soil moisture against field capacity, and what the satellite shows. */
export function ZonesPanel({ plot, version }: ZonesPanelProps) {
  const zones = useResource(useCallback(() => api.zones(plot.id), [plot.id]), version);
  const imagery = useResource(useCallback(() => api.imagery(plot.id), [plot.id]), version);
  const scene = imagery.data?.scene;

  return (
    <Panel title="Zonas" error={zones.error ?? imagery.error}>
      {scene ? (
        <p className="muted">
          Imagen satelital del {scene.acquired_on}
          {scene.synthetic ? " (sintética)" : ""}. Vigor bajo: NDVI medio menor que{" "}
          {formatNumber(scene.low_ndvi_threshold, 2)}.
          {scene.segmentation_note ? ` ${scene.segmentation_note}` : ""}
        </p>
      ) : (
        <p className="muted">No hay imagen satelital para esta parcela.</p>
      )}
      <div className="zone-grid">
        {zones.data?.map((zone) => (
          <ZoneCard
            key={zone.id}
            zone={zone}
            version={version}
            imagery={imagery.data?.zones.find((z) => z.zone_id === zone.id) ?? null}
          />
        ))}
      </div>
    </Panel>
  );
}

interface ZoneCardProps {
  zone: Zone;
  version: number;
  imagery: ZoneImagery | null;
}

function ZoneCard({ zone, version, imagery }: ZoneCardProps) {
  const readings = useResource(useCallback(() => api.readings(zone.id, 48), [zone.id]), version);
  const moisture = readings.data?.find((s) => s.kind === "soil_moisture") ?? null;
  const latest = moisture?.readings.at(-1)?.value;

  return (
    <article className={`zone-card ${imagery?.low_vigor ? "zone-card--low" : ""}`}>
      <h3>{zone.name}</h3>
      <p>
        Humedad del suelo:{" "}
        <strong>{latest === undefined ? "sin lectura" : `${formatNumber(latest)} %`}</strong> de{" "}
        {formatNumber(zone.field_capacity_pct)} % de capacidad de campo
      </p>
      {moisture ? <MoistureSparkline readings={moisture} fieldCapacity={zone.field_capacity_pct} /> : null}
      {imagery ? (
        <ul className="zone-card__imagery">
          <li>NDVI medio: {imagery.ndvi_mean === null ? "desconocido" : formatNumber(imagery.ndvi_mean, 3)}</li>
          <li>
            Píxeles con NDVI bajo:{" "}
            {imagery.low_ndvi_pct === null ? "desconocido" : `${formatNumber(imagery.low_ndvi_pct)} %`}
          </li>
          <li>
            Suelo desnudo:{" "}
            {imagery.bare_soil_pct === null
              ? "desconocido"
              : `aproximadamente ${formatNumber(imagery.bare_soil_pct, 0)} %`}
          </li>
          {imagery.low_vigor ? <li className="badge badge--warn">Vigor bajo</li> : null}
        </ul>
      ) : null}
    </article>
  );
}

const WIDTH = 220;
const HEIGHT = 48;

/** Soil moisture over time against field capacity: hand-written SVG (D068). */
function MoistureSparkline({ readings, fieldCapacity }: { readings: SensorReadings; fieldCapacity: number }) {
  const values = readings.readings.map((r) => r.value);
  if (values.length < 2) return null;
  const top = Math.max(fieldCapacity, ...values) * 1.1;
  const x = (i: number) => (i / (values.length - 1)) * WIDTH;
  const y = (v: number) => HEIGHT - (v / top) * HEIGHT;
  const points = values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return (
    <svg className="sparkline" viewBox={`0 0 ${WIDTH} ${HEIGHT}`}>
      <title>Humedad del suelo en el tiempo, con la capacidad de campo</title>
      <line x1={0} x2={WIDTH} y1={y(fieldCapacity)} y2={y(fieldCapacity)} className="sparkline__capacity" />
      <polyline points={points} className="sparkline__line" />
    </svg>
  );
}
