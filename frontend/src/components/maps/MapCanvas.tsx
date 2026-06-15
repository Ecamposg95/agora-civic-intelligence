import { useEffect, useRef } from "react";
import maplibregl, {
  type GeoJSONSource,
  type StyleSpecification,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import type { AreasResponse } from "@/types/maps";

export interface WmsOverlay {
  id: string; // e.g. "wms:secciones"
  tiles: string[];
  visible: boolean;
}

interface MapCanvasProps {
  /** GeoJSON FeatureCollection of areas (may be empty). */
  areas: AreasResponse | null;
  /** Whether the territorial areas overlay should be shown. */
  showAreas: boolean;
  /** INE SIGE WMS raster overlays (optional). */
  wmsLayers?: WmsOverlay[];
}

const AREAS_SOURCE = "agora-areas";
const AREAS_FILL = "agora-areas-fill";
const AREAS_LINE = "agora-areas-line";

// Inline OSM raster basemap — no API key required.
const BASE_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [
    {
      id: "osm",
      type: "raster",
      source: "osm",
      paint: { "raster-saturation": -0.85, "raster-brightness-max": 0.85 },
    },
  ],
};

const EMPTY_FC: AreasResponse = { type: "FeatureCollection", features: [] };

// The API allows null geometries; MapLibre's GeoJSON typing is stricter.
// Cast at the boundary — MapLibre simply skips features without geometry.
const asGeoJSON = (fc: AreasResponse): GeoJSON.FeatureCollection =>
  fc as unknown as GeoJSON.FeatureCollection;

export function MapCanvas({ areas, showAreas, wmsLayers = [] }: MapCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const readyRef = useRef(false);
  const wmsAddedRef = useRef<Set<string>>(new Set());

  // Initialize the map once.
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASE_STYLE,
      center: [-102.55, 23.63], // México
      zoom: 4.2,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    mapRef.current = map;

    map.on("load", () => {
      readyRef.current = true;
      map.addSource(AREAS_SOURCE, {
        type: "geojson",
        data: asGeoJSON(EMPTY_FC),
      });
      map.addLayer({
        id: AREAS_FILL,
        type: "fill",
        source: AREAS_SOURCE,
        paint: { "fill-color": "#4f9cff", "fill-opacity": 0.18 },
      });
      map.addLayer({
        id: AREAS_LINE,
        type: "line",
        source: AREAS_SOURCE,
        paint: { "line-color": "#2dd4bf", "line-width": 1.5 },
      });
    });

    return () => {
      map.remove();
      mapRef.current = null;
      readyRef.current = false;
      wmsAddedRef.current = new Set();
    };
  }, []);

  // Push area data + visibility whenever inputs change.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const apply = () => {
      const source = map.getSource(AREAS_SOURCE) as GeoJSONSource | undefined;
      if (source) source.setData(asGeoJSON(areas ?? EMPTY_FC));
      const visibility = showAreas ? "visible" : "none";
      if (map.getLayer(AREAS_FILL))
        map.setLayoutProperty(AREAS_FILL, "visibility", visibility);
      if (map.getLayer(AREAS_LINE))
        map.setLayoutProperty(AREAS_LINE, "visibility", visibility);
    };

    if (readyRef.current) apply();
    else map.once("load", apply);
  }, [areas, showAreas]);

  // INE SIGE WMS raster overlays — added beneath the areas overlay.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const apply = () => {
      for (const layer of wmsLayers) {
        const id = layer.id;
        if (!wmsAddedRef.current.has(id)) {
          if (!map.getSource(id)) {
            map.addSource(id, { type: "raster", tiles: layer.tiles, tileSize: 256 });
          }
          const beforeId = map.getLayer(AREAS_FILL) ? AREAS_FILL : undefined;
          map.addLayer(
            { id, type: "raster", source: id, paint: { "raster-opacity": 0.85 } },
            beforeId,
          );
          wmsAddedRef.current.add(id);
        }
        if (map.getLayer(id)) {
          map.setLayoutProperty(id, "visibility", layer.visible ? "visible" : "none");
        }
      }
    };

    if (readyRef.current) apply();
    else map.once("load", apply);
  }, [wmsLayers]);

  return (
    <div className="relative h-full w-full overflow-hidden rounded-card border border-line">
      <div ref={containerRef} className="absolute inset-0" />
    </div>
  );
}
