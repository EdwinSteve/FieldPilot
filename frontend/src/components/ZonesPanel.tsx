import { useCallback } from "react";
import { api } from "../api/endpoints";
import { useResource } from "../hooks/useResource";
import { seriesRange, toPoints } from "../lib/chart";
import { formatNumber } from "../lib/format";
import { arcPath, gaugeFraction, polar } from "../lib/gauge";
import type { Plot, Reading, Zone } from "../types/api";
import { Panel } from "./Panel";

interface ZonesPanelProps {
  plot: Plot;
  version: number;
}

/** Each zone: how full the soil is, and how it got there. */
export function ZonesPanel({ plot, version }: ZonesPanelProps) {
  const zones = useResource(useCallback(() => api.zones(plot.id), [plot.id]), version);
  const imagery = useResource(useCallback(() => api.imagery(plot.id), [plot.id]), version);

  return (
    <Panel title="Zones" error={zones.error ?? imagery.error} icon="drop" loading={zones.loading}>
      {zones.data?.length === 0 ? <p className="muted">No zones yet.</p> : null}
      <div className="zone-grid">
        {zones.data?.map((zone) => (
          <ZoneCard
            key={zone.id}
            zone={zone}
            version={version}
            lowVigor={imagery.data?.zones.find((z) => z.zone_id === zone.id)?.low_vigor ?? false}
          />
        ))}
      </div>
    </Panel>
  );
}

interface ZoneCardProps {
  zone: Zone;
  version: number;
  lowVigor: boolean;
}

function ZoneCard({ zone, version, lowVigor }: ZoneCardProps) {
  const readings = useResource(useCallback(() => api.readings(zone.id, 48), [zone.id]), version);
  const moisture = readings.data?.find((s) => s.kind === "soil_moisture") ?? null;
  const temperature = readings.data?.find((s) => s.kind === "temperature") ?? null;
  const latest = moisture?.readings.at(-1)?.value;

  return (
    <article className={`zone-card ${lowVigor ? "zone-card--low" : ""}`}>
      <div className="zone-card__head">
        <h3>{zone.name}</h3>
        {lowVigor ? <span className="badge badge--warn">Low vigour</span> : null}
      </div>
      <div className="zone-card__gauge-row">
        <MoistureGauge latest={latest} fieldCapacity={zone.field_capacity_pct} />
        <p>
          Humedad del suelo:{" "}
          <strong>{latest === undefined ? "no reading" : `${formatNumber(latest)} %`}</strong> of{" "}
          {formatNumber(zone.field_capacity_pct)} % de capacidad de campo
        </p>
      </div>
      {moisture ? (
        <LineChart
          readings={moisture.readings}
          lineClass="chart__line"
          title={`Soil moisture in ${zone.name}, with the field capacity`}
          reference={{ value: zone.field_capacity_pct, label: "field capacity" }}
        />
      ) : null}
      {temperature && temperature.readings.length > 0 ? (
        <LineChart
          readings={temperature.readings}
          lineClass="chart__line--sky"
          title={`Temperature in ${zone.name}`}
        />
      ) : null}
    </article>
  );
}

const GAUGE_START = -120;
const GAUGE_SWEEP = 240;
const GAUGE_MAX = 1.2; // the dial reads up to 120 % of field capacity
const SAFETY_LIMIT = 0.85; // do not irrigate above 85 % of field capacity

/** How full the soil is, with the 85 % safety limit marked on the dial. */
function MoistureGauge({
  latest,
  fieldCapacity,
}: {
  latest: number | undefined;
  fieldCapacity: number;
}) {
  const fraction = gaugeFraction(latest, fieldCapacity);
  const shown = Math.min(fraction, GAUGE_MAX);
  const end = GAUGE_START + (shown / GAUGE_MAX) * GAUGE_SWEEP;
  const limitAngle = GAUGE_START + (SAFETY_LIMIT / GAUGE_MAX) * GAUGE_SWEEP;
  const tickFrom = polar(60, 60, 40, limitAngle);
  const tickTo = polar(60, 60, 50, limitAngle);
  return (
    <svg className="gauge" viewBox="0 0 120 120">
      <title>
        {latest === undefined
          ? "No moisture reading"
          : `${formatNumber(latest)} % of ${formatNumber(fieldCapacity)} % field capacity`}
      </title>
      <path
        d={arcPath(60, 60, 45, GAUGE_START, GAUGE_START + GAUGE_SWEEP)}
        className="gauge__track"
      />
      {fraction > 0 ? (
        <path d={arcPath(60, 60, 45, GAUGE_START, end)} className="gauge__fill" />
      ) : null}
      <line x1={tickFrom.x} y1={tickFrom.y} x2={tickTo.x} y2={tickTo.y} className="gauge__limit">
        <title>Safety limit: 85 % of the field capacity</title>
      </line>
      <text x="60" y="62" textAnchor="middle" className="gauge__value">
        {latest === undefined ? "—" : `${formatNumber(latest)} %`}
      </text>
      <text x="60" y="78" textAnchor="middle" className="gauge__caption">
        de {formatNumber(fieldCapacity)} %
      </text>
    </svg>
  );
}

const CHART_WIDTH = 220;
const CHART_HEIGHT = 64;

interface LineChartProps {
  readings: Reading[];
  lineClass: string;
  title: string;
  reference?: { value: number; label: string };
}

/** Sensor readings over time, oldest first, with an optional reference line. */
function LineChart({ readings, lineClass, title, reference }: LineChartProps) {
  const values = readings.map((r) => r.value);
  const range = seriesRange(reference ? [...values, reference.value] : values);
  if (values.length < 2 || range === null) return null;
  const span = range.max - range.min || 1;
  const referenceY =
    reference === undefined ? null : CHART_HEIGHT - ((reference.value - range.min) / span) * CHART_HEIGHT;
  return (
    <svg className="chart" viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}>
      <title>{title}</title>
      {referenceY === null ? null : (
        <line x1={0} x2={CHART_WIDTH} y1={referenceY} y2={referenceY} className="chart__reference">
          <title>{reference?.label}</title>
        </line>
      )}
      <polyline points={toPoints(values, CHART_WIDTH, CHART_HEIGHT, range)} className={lineClass} />
    </svg>
  );
}
