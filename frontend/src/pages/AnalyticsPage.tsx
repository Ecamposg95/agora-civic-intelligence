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
    <AppLayout title="Activity Analytics" crumb="Operational Intelligence">
      <div className="mb-6">
        <div className="eyebrow">Operational intelligence</div>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">
          Activity Analytics
        </h1>
        <p className="mt-1 max-w-xl text-sm text-ink-muted">
          Tenant-scoped platform activity from the audit trail. Civic
          participation series will appear here as padrón and PREP pipelines are
          onboarded.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-state-critical/40 bg-state-critical/10 px-3 py-2 text-sm text-state-critical">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Eventos por día (últimos 14 días)">
          {data ? (
            <ParticipationChart
              data={data.trends.activity}
              height={260}
              valueFormat="number"
              seriesLabel="Eventos"
            />
          ) : (
            <div className="h-[260px] animate-pulse rounded-lg bg-panel-hover" />
          )}
        </Card>

        <Card title="Methodology & governance">
          <p className="text-sm leading-relaxed text-ink-muted">
            Metrics are aggregated live from the database and are tenant-scoped.
            Individual records are never exposed; all access is audit-logged. The
            activity series is built from the audit trail.
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
