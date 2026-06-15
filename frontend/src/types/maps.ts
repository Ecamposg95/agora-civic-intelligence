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
