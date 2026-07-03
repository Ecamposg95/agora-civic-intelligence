import { apiClient } from "./client";

export interface AreaHit {
  id: string;
  name: string;
  level: string;
  code: string | null;
}

export async function searchAreas(q: string, level?: string): Promise<AreaHit[]> {
  const params: Record<string, string> = {};
  if (q) params.q = q;
  if (level) params.level = level;
  const { data } = await apiClient.get<AreaHit[]>("/territory/search", { params });
  return data;
}

export async function assignTerritory(
  userId: string,
  areaId: string | null,
): Promise<void> {
  await apiClient.put(`/users/${userId}/territorio`, { area_id: areaId });
}
