export interface SourceInfo {
  id: string;
  name: string;
  kind: "api" | "wms" | "download" | "portal";
  base_url: string;
  formats: string[];
  auth_required: boolean;
  notes: string;
}

export interface DatasetSummary {
  id: string;
  title: string;
  organization: string | null;
  formats: string[];
  url: string | null;
}

export interface WmsLayer {
  id: string;
  name: string;
  level: string;
  type: string;
  tiles: string[];
  tileSize: number;
  srid: number;
}

export interface WmsLayersResponse {
  configured: boolean;
  layers: WmsLayer[];
}
