import { apiClient } from "./client";
import type {
  IeemDataset,
  IeemDatasetRef,
  WbIndicator,
  WbIndicatorRef,
} from "@/types/intel";

export async function getIeemDatasets(): Promise<IeemDatasetRef[]> {
  const { data } = await apiClient.get<{ items: IeemDatasetRef[] }>(
    "/intel/ieem/datasets",
  );
  return data.items;
}
export async function getIeemDataset(key: string): Promise<IeemDataset> {
  const { data } = await apiClient.get<IeemDataset>(`/intel/ieem/${key}`);
  return data;
}
export async function getWbIndicators(): Promise<WbIndicatorRef[]> {
  const { data } = await apiClient.get<{ items: WbIndicatorRef[] }>(
    "/intel/worldbank/indicators",
  );
  return data.items;
}
export async function getWbIndicator(code: string): Promise<WbIndicator> {
  const { data } = await apiClient.get<WbIndicator>(
    `/intel/worldbank/indicator/${code}`,
  );
  return data;
}
