import { apiClient } from "./client";
import type {
  DatasetSummary,
  SourceInfo,
  WmsLayersResponse,
} from "@/types/sources";

export async function getSources(): Promise<SourceInfo[]> {
  const { data } = await apiClient.get<SourceInfo[]>("/sources");
  return data;
}

export async function searchDatasets(
  q: string,
  ineOnly = true,
): Promise<DatasetSummary[]> {
  const { data } = await apiClient.get<DatasetSummary[]>("/sources/datasets", {
    params: { q, ine_only: ineOnly, rows: 20 },
  });
  return data;
}

export async function getWmsLayers(): Promise<WmsLayersResponse> {
  const { data } = await apiClient.get<WmsLayersResponse>("/maps/wms-layers");
  return data;
}
