import { useEffect, useState } from "react";

import { getOverview } from "@/api/analytics";
import { AppLayout } from "@/components/layout/AppLayout";
import { ParticipationChart } from "@/components/dashboards/ParticipationChart";
import { Card } from "@/components/ui/Card";
import type { AnalyticsOverview } from "@/types/analytics";

export function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getOverview()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <AppLayout title="Participation Analytics" crumb="Civic Engagement">
      <div className="mb-6">
        <div className="eyebrow">Engagement intelligence</div>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">
          Participation Analytics
        </h1>
        <p className="mt-1 max-w-xl text-sm text-ink-muted">
          Longitudinal analysis of civic participation across territories and
          electoral cycles, governed for privacy and auditability.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-state-critical/40 bg-state-critical/10 px-3 py-2 text-sm text-state-critical">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Participation by quarter">
          {data ? (
            <ParticipationChart data={data.trends.participation} height={260} />
          ) : (
            <div className="h-[260px] animate-pulse rounded-lg bg-panel-hover" />
          )}
        </Card>

        <Card title="Methodology & governance">
          <p className="text-sm leading-relaxed text-ink-muted">
            Metrics are aggregated from governed electoral datasets. Individual
            records are never exposed; all access is audit-logged and
            tenant-scoped. Replace this placeholder series with live pipelines as
            data sources are onboarded.
          </p>
          <div className="mt-4 space-y-2">
            <div className="flex items-center justify-between rounded-lg border border-line bg-bg-sunken px-3 py-2.5">
              <span className="text-sm text-ink">Aggregation</span>
              <span className="pill border-accent/30 bg-accent/10 text-accent">
                Tenant-scoped
              </span>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-line bg-bg-sunken px-3 py-2.5">
              <span className="text-sm text-ink">Privacy</span>
              <span className="pill border-teal/30 bg-teal/10 text-teal">
                By design
              </span>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-line bg-bg-sunken px-3 py-2.5">
              <span className="text-sm text-ink">Auditability</span>
              <span className="pill border-state-warning/30 bg-state-warning/10 text-state-warning">
                Full trail
              </span>
            </div>
          </div>
        </Card>
      </div>
    </AppLayout>
  );
}
