export interface AnalyticsSummary {
  electoral_areas: number;
  organizations: number;
  users: number;
  data_sources: number;
}

export interface TrendPoint {
  period: string;
  value: number;
}

export interface AnalyticsAlert {
  level: "info" | "warning" | "critical";
  title: string;
  detail: string;
}

export interface AnalyticsOverview {
  summary: AnalyticsSummary;
  coverage: { level: string; count: number }[];
  trends: {
    activity: TrendPoint[];
  };
  alerts: AnalyticsAlert[];
  generated_at: string;
}
