import { useCallback, useState } from "react";
import { api } from "../api/endpoints";
import { useResource } from "../hooks/useResource";
import { formatNumber } from "../lib/format";
import { boxRect, ndviPosition } from "../lib/imagery";
import type { Plot, ZoneImagery } from "../types/api";
import { Panel } from "./Panel";

interface SatellitePanelProps {
  plot: Plot;
  version: number;
}

/** The latest scene with SAM's boxes, zone outlines and NDVI per zone (D059, D073). */
export function SatellitePanel({ plot, version }: SatellitePanelProps) {
  const zones = useResource(useCallback(() => api.zones(plot.id), [plot.id]), version);
  const imagery = useResource(useCallback(() => api.imagery(plot.id), [plot.id]), version);
  const [imageFailed, setImageFailed] = useState(false);
  const scene = imagery.data?.scene;
  const nameOf = (zoneId: number) => zones.data?.find((z) => z.id === zoneId)?.name ?? `Zona ${zoneId}`;

  return (
    <Panel title="Vista satelital" error={zones.error ?? imagery.error} icon="satellite">
      {scene ? (
        <p className="muted">
          Imagen del {scene.acquired_on}
          {scene.synthetic ? " (sintética)" : ""}. Vigor bajo: NDVI medio menor que{" "}
          {formatNumber(scene.low_ndvi_threshold, 2)}.
          {scene.segmentation_note ? ` ${scene.segmentation_note}` : ""}
        </p>
      ) : (
        <p className="muted">No hay imagen satelital para esta parcela.</p>
      )}
      {scene && !imageFailed ? (
        <div className="satellite-frame">
          <img
            src={api.imageryImageUrl(plot.id)}
            alt={`Imagen satelital de ${plot.name} del ${scene.acquired_on}`}
            className="satellite-frame__img"
            onError={() => setImageFailed(true)}
          />
          <svg
            className="satellite-frame__overlay"
            viewBox="0 0 1 1"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            {(imagery.data?.zones ?? []).map((zone) => (
              <ZoneOutline key={zone.zone_id} zone={zone} />
            ))}
            {(imagery.data?.boxes ?? []).map((box) => (
              <rect
                key={`${box.x1},${box.y1},${box.x2},${box.y2}`}
                {...boxRect(box)}
                className="satellite-frame__box"
                vectorEffect="non-scaling-stroke"
              />
            ))}
          </svg>
          {(imagery.data?.zones ?? []).map((zone) => (
            <span
              key={zone.zone_id}
              className="satellite-frame__tag"
              style={{ left: `${zone.area.x1 * 100}%`, top: `${zone.area.y1 * 100}%` }}
            >
              {nameOf(zone.zone_id)}
            </span>
          ))}
        </div>
      ) : null}
      {scene && imageFailed ? <p className="muted">No se pudo cargar la imagen.</p> : null}
      <ul className="ndvi-list">
        {(imagery.data?.zones ?? []).map((zone) => (
          <li key={zone.zone_id} className="ndvi-list__item">
            <strong>{nameOf(zone.zone_id)}</strong>
            <NdviScale zone={zone} />
            <span>
              Suelo desnudo:{" "}
              {zone.bare_soil_pct === null
                ? "desconocido"
                : `aproximadamente ${formatNumber(zone.bare_soil_pct, 0)} %`}
            </span>
            {zone.low_vigor ? <span className="badge badge--warn">Vigor bajo</span> : null}
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function ZoneOutline({ zone }: { zone: ZoneImagery }) {
  return (
    <rect
      {...boxRect(zone.area)}
      className="satellite-frame__zone"
      vectorEffect="non-scaling-stroke"
    />
  );
}

function NdviScale({ zone }: { zone: ZoneImagery }) {
  const position = ndviPosition(zone.ndvi_mean);
  return (
    <span className="ndvi-scale">
      <span className="ndvi-scale__bar" aria-hidden="true">
        {position === null ? null : (
          <span className="ndvi-scale__marker" style={{ left: `${position}%` }} />
        )}
      </span>
      <span>
        NDVI {zone.ndvi_mean === null ? "desconocido" : formatNumber(zone.ndvi_mean, 3)}
      </span>
    </span>
  );
}
