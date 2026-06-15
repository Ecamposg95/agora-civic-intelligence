export interface AnalyticsSummary {
  registered_voters: number;
  electoral_areas: number;
  active_institutions: number;
  participation_rate: number;
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
  trends: {
    participation: TrendPoint[];
  };
  alerts: AnalyticsAlert[];
}
