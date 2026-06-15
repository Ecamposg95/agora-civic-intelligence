export type LayerCategory = "electoral" | "analytics" | "territorial";
export type GeometryType = "point" | "polygon" | "raster";

export interface MapLayer {
  id: string;
  name: string;
  category: LayerCategory;
  geometry_type: GeometryType;
  srid: number;
  visible: boolean;
  description: string;
}

export interface LayersResponse {
  layers: MapLayer[];
}

export interface AreaProperties {
  id: string;
  name: string;
  code: string | null;
  level: string;
  organization_id: string;
}

export interface AreaFeature {
  type: "Feature";
  geometry: GeoJSON.Geometry | null;
  properties: AreaProperties;
}

export interface AreasResponse {
  type: "FeatureCollection";
  features: AreaFeature[];
}

/** Deterministic sample metric in [0,1] from an area id — clearly labelled
 *  "datos de muestra" in the UI until real per-area metrics exist. */
export function sampleMetric(id: string): number {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
  return 0.45 + ((h % 1000) / 1000) * 0.45; // 0.45–0.90
}
