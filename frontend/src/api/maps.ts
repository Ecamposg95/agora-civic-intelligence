import { apiClient } from "./client";
import type { AreasResponse, LayersResponse } from "@/types/maps";

export async function getLayers(): Promise<LayersResponse> {
  const { data } = await apiClient.get<LayersResponse>("/maps/layers");
  return data;
}

export async function getAreas(): Promise<AreasResponse> {
  const { data } = await apiClient.get<AreasResponse>("/maps/areas");
  return data;
}
