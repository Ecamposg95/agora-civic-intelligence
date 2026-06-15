import { getWbIndicator } from "@/api/intel";
import { AppLayout } from "@/components/layout/AppLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import { ParticipationChart } from "@/components/dashboards/ParticipationChart";
import { Card } from "@/components/ui/Card";
import { DataState } from "@/components/ui/DataState";
import { useAsync } from "@/hooks/useAsync";

const CODES = [
  { code: "NY.GDP.MKTP.CD", label: "PIB (USD)" },
  { code: "SP.POP.TOTL", label: "Población" },
  { code: "FP.CPI.TOTL.ZG", label: "Inflación (%)" },
  { code: "SL.UEM.TOTL.ZS", label: "Desempleo (%)" },
];

const compact = new Intl.NumberFormat("es-MX", { notation: "compact" });

function IndicatorCard({ code, label }: { code: string; label: string }) {
  const { data, loading, error, reload } = useAsync(
    () => getWbIndicator(code),
    [code],
  );
  const series = (data?.points ?? []).map((p) => ({
    period: String(p.year),
    value: p.value,
  }));

  return (
    <Card title={label} accentDot className="card-premium hud-corners">
      <DataState
        loading={loading}
        error={error}
        onRetry={reload}
        isEmpty={!!data && series.length === 0}
        emptyMessage="Sin serie disponible para este indicador."
        skeleton={
          <div className="h-[190px] animate-pulse rounded-lg bg-panel-hover" />
        }
      >
        {data && (
          <>
            <div className="mb-2 font-display text-2xl font-bold tabular-nums text-ink">
              {data.latest ? compact.format(data.latest.value) : "—"}
              {data.latest && (
                <span className="ml-2 font-mono text-xs text-ink-faint">
                  {data.latest.year}
                </span>
              )}
            </div>
            <ParticipationChart
              data={series}
              height={160}
              valueFormat="number"
              seriesLabel={label}
            />
            <p className="mt-3 text-[11px] text-ink-faint">
              Fuente: {data.source}
            </p>
          </>
        )}
      </DataState>
    </Card>
  );
}

export function WorldBankPage() {
  return (
    <AppLayout title="Indicadores Nacionales" crumb="World Bank · Macro">
      <PageHeader
        eyebrow="Contexto macro"
        title="Indicadores"
        accent="Nacionales"
        subtitle="Series macroeconómicas de México (Banco Mundial). Datos reales."
      />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {CODES.map((c) => (
          <IndicatorCard key={c.code} {...c} />
        ))}
      </div>
    </AppLayout>
  );
}
