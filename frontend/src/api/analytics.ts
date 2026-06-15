import { apiClient } from "./client";
import type { AnalyticsOverview } from "@/types/analytics";

export async function getOverview(): Promise<AnalyticsOverview> {
  const { data } = await apiClient.get<AnalyticsOverview>("/analytics/overview");
  return data;
}
