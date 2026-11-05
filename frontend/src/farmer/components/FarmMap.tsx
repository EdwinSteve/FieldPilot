import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useRef } from "react";
import { en } from "../i18n/en";
import type { LatLng } from "../lib/farmOutline";

export type MapLayer = "photo" | "map";

/** Most of Colombia, before the farmer's town is found. */
const COLOMBIA_CENTRE: LatLng = { lat: 4.6, lng: -74.1 };
const COUNTRY_ZOOM = 6;
const TOWN_ZOOM = 15;

/** Esri's satellite photos with its place names on top: the farmer finds their field in a photo. */
function photoLayers(): L.Layer[] {
  const esri = "https://server.arcgisonline.com/ArcGIS/rest/services";
  return [
    L.tileLayer(`${esri}/World_Imagery/MapServer/tile/{z}/{y}/{x}`, {
      maxNativeZoom: 18,
      maxZoom: 19,
      attribution: "Tiles © Esri: Maxar, Earthstar Geographics and the GIS User Community",
    }),
    L.tileLayer(`${esri}/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}`, {
      maxNativeZoom: 18,
      maxZoom: 19,
    }),
  ];
}

function plainLayers(): L.Layer[] {
  return [
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }),
  ];
}

function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

interface FarmMapProps {
  /** Where the map flies to: the farmer's town once found. */
  centre: LatLng | null;
  outline: readonly LatLng[];
  layer: MapLayer;
  onAdd: (point: LatLng) => void;
  /** Hands the parent a way to add the point under the crosshair. */
  onReady: (addAtCentre: () => void) => void;
}

/** The map the farmer outlines their farm on. Leaflet draws; React only says what to draw. */
export function FarmMap({ centre, outline, layer, onAdd, onReady }: FarmMapProps) {
  const element = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const shapes = useRef<L.LayerGroup | null>(null);
  const tiles = useRef<L.Layer[]>([]);
  const add = useRef(onAdd);
  const ready = useRef(onReady);
  const start = useRef(centre);

  useEffect(() => {
    add.current = onAdd;
    ready.current = onReady;
  });

  useEffect(() => {
    if (element.current === null) return undefined;
    const first = start.current ?? COLOMBIA_CENTRE;
    const created = L.map(element.current, {
      center: [first.lat, first.lng],
      zoom: start.current === null ? COUNTRY_ZOOM : TOWN_ZOOM,
      zoomControl: true,
    });
    created.on("click", (event: L.LeafletMouseEvent) =>
      add.current({ lat: event.latlng.lat, lng: event.latlng.lng }),
    );
    shapes.current = L.layerGroup().addTo(created);
    map.current = created;
    ready.current(() => {
      const middle = created.getCenter();
      add.current({ lat: middle.lat, lng: middle.lng });
    });
    return () => {
      created.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    const current = map.current;
    if (current === null) return;
    tiles.current.forEach((tile) => tile.remove());
    tiles.current = (layer === "photo" ? photoLayers() : plainLayers()).map((tile) =>
      tile.addTo(current),
    );
  }, [layer]);

  useEffect(() => {
    if (centre !== null) map.current?.setView([centre.lat, centre.lng], TOWN_ZOOM);
  }, [centre]);

  useEffect(() => {
    const group = shapes.current;
    if (group === null) return;
    group.clearLayers();
    const edge = token("--color-ring");
    const corners = outline.map((point) => [point.lat, point.lng] as L.LatLngTuple);
    if (corners.length >= 2) {
      L.polygon(corners, { color: edge, weight: 4, fillColor: edge, fillOpacity: 0.2 }).addTo(group);
    }
    corners.forEach((corner) =>
      L.circleMarker(corner, {
        radius: 9,
        color: token("--color-surface"),
        weight: 3,
        fillColor: edge,
        fillOpacity: 1,
      }).addTo(group),
    );
  }, [outline]);

  return (
    <div className="relative overflow-hidden rounded-tile">
      <div ref={element} role="application" aria-label={en.setup.mapLabel} className="h-80 w-full" />
      {/* The crosshair marks where "Add corner here" puts a corner. */}
      <span
        aria-hidden="true"
        className="pointer-events-none absolute top-1/2 left-1/2 z-[400] size-7 -translate-x-1/2 -translate-y-1/2 rounded-full border-3 border-surface shadow-bubble"
      />
    </div>
  );
}

export default FarmMap;
