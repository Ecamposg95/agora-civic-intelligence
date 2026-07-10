// frontend/src/modules/reportes/ReportesPage.tsx
import { useMemo, type ReactNode } from "react";

import { getExecutiveDashboard } from "@/api/dashboard";
import { AreaTrend } from "@/components/charts/AreaTrend";
import { Bars } from "@/components/charts/Bars";
import { ChartFrame } from "@/components/charts/ChartFrame";
import { AppLayout } from "@/components/layout/AppLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { DataState } from "@/components/ui/DataState";
import { MetricCard } from "@/components/ui/MetricCard";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { SkeletonCard } from "@/components/ui/SkeletonCard";
import {
  AlertIcon,
  AnalyticsIcon,
  DatabaseIcon,
  MapIcon,
  ShieldIcon,
  VotersIcon,
} from "@/components/ui/icons";
import { useAsync } from "@/hooks/useAsync";
import type { ExecutiveDashboard } from "@/api/dashboard";

import { downloadCSV } from "./export";

const intFmt = new Intl.NumberFormat("es-MX");
const pctFmt = (n: number) => `${intFmt.format(Math.round(n))}%`;

/** Localized, human-readable timestamp for the print/export provenance line. */
function formatTimestamp(date: Date): string {
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(date);
}

export function ReportesPage() {
  // Campaign executive briefing — same payload the Command Center renders.
  const dashboardState = useAsync<ExecutiveDashboard>(() => getExecutiveDashboard(), []);

  const dashboard = dashboardState.data;

  const isEmpty =
    !dashboardState.loading &&
    !dashboardState.error &&
    dashboard === null;

  const handleCSV = () => {
    if (dashboard) downloadCSV(dashboard);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <AppLayout title="Reportes de Campaña" crumb="Gobernanza">
      <PageHeader
        eyebrow="Campaña"
        title="Reporte"
        accent="de Campaña"
        subtitle="Briefing ejecutivo compuesto de datos reales de campaña: promoción, afiliación, atención ciudadana y cobertura."
        actions={
          <div className="flex flex-wrap items-center gap-3 print:hidden">
            <button
              type="button"
              onClick={handleCSV}
              disabled={!dashboard}
              className="btn-ghost disabled:cursor-not-allowed disabled:opacity-40"
            >
              <DatabaseIcon width={16} height={16} />
              Exportar CSV
            </button>
            <button
              type="button"
              onClick={handlePrint}
              disabled={!dashboard}
              className="btn-primary disabled:cursor-not-allowed disabled:opacity-40"
            >
              <AnalyticsIcon width={16} height={16} />
              Imprimir / PDF
            </button>
          </div>
        }
      />

      <DataState
        loading={dashboardState.loading}
        error={dashboardState.error}
        isEmpty={isEmpty}
        onRetry={dashboardState.reload}
        emptyMessage="Sin datos de campaña todavía — captura pendiente."
        skeleton={
          <div className="space-y-4">
            {/* P-2: SkeletonCard replaces raw animate-pulse divs */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <SkeletonCard key={i} lines={2} />
              ))}
            </div>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-[360px_1fr]">
              <SkeletonCard lines={5} />
              <SkeletonCard lines={1} className="min-h-[340px]" />
            </div>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <SkeletonCard lines={4} />
              <SkeletonCard lines={4} />
            </div>
          </div>
        }
      >
        {dashboard && <Briefing dashboard={dashboard} />}
      </DataState>
    </AppLayout>
  );
}

interface BriefingProps {
  dashboard: ExecutiveDashboard;
}

/**
 * The printable briefing region. The `print:` utilities flip this block to a
 * clean white/black document and hide chrome so the PDF/print output reads as
 * an institutional campaign report. Only real values are shown; the export
 * timestamp is generated client-side at print/export time.
 */
function Briefing({ dashboard }: BriefingProps) {
  // Defensive: a partial/degraded payload should never white-screen the page.
  const tendencia = dashboard.tendencia ?? [];
  const porSeccionTop = dashboard.por_seccion_top ?? [];
  const casosPorEstado = dashboard.casos_por_estado ?? [];
  const alertas = dashboard.alertas ?? [];

  const now = useMemo(() => new Date(), []);

  const promovidosContext = useMemo(() => {
    if (dashboard.promovidos.meta == null) return undefined;
    const pct =
      dashboard.promovidos.pct != null ? ` · ${intFmt.format(dashboard.promovidos.pct)}%` : "";
    return `meta ${intFmt.format(dashboard.promovidos.meta)}${pct}`;
  }, [dashboard.promovidos]);

  const afiliadosContext = useMemo(
    () => `${intFmt.format(dashboard.afiliados.validados)} validados`,
    [dashboard.afiliados],
  );

  const casosContext = useMemo(
    () => `${intFmt.format(dashboard.casos.sla_vencidos)} con SLA vencido`,
    [dashboard.casos],
  );

  const casosTone: "critical" | "teal" = dashboard.casos.sla_vencidos > 0 ? "critical" : "teal";

  const coberturaContext = useMemo(
    () =>
      `${intFmt.format(dashboard.cobertura.al_dia)} al día · ${intFmt.format(
        dashboard.cobertura.en_riesgo,
      )} en riesgo`,
    [dashboard.cobertura],
  );

  // P-8: reveal wraps the primary content block for entrance animation
  return (
    <div className="reveal space-y-6 print:space-y-3 print:bg-white print:p-0 print:text-black">
      {/* Print-only header (hidden on screen — screen uses PageHeader). */}
      <div className="hidden print:mb-4 print:block print:border-b print:border-black/20 print:pb-3">
        <h1 className="text-2xl font-bold">Atenea · Reporte de Campaña</h1>
        <p className="text-sm">
          Briefing ejecutivo compuesto de datos reales de campaña.
        </p>
        <p className="mt-1 text-xs">Generado: {formatTimestamp(now)}</p>
      </div>

      {/* KPI summary */}
      <div className="space-y-4 print:space-y-2">
        <SectionHeading eyebrow="Panorama" title="Indicadores clave" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 print:grid-cols-4 print:gap-2">
          <KpiCard
            label="Promovidos"
            value={dashboard.promovidos.total}
            context={promovidosContext}
            icon={<VotersIcon />}
            tone="warm"
            delay={60}
          />
          <KpiCard
            label="Afiliados"
            value={dashboard.afiliados.total}
            context={afiliadosContext}
            icon={<ShieldIcon />}
            tone="accent"
            delay={120}
          />
          <KpiCard
            label="Casos abiertos"
            value={dashboard.casos.abiertos}
            context={casosContext}
            icon={<AlertIcon />}
            tone={casosTone}
            delay={180}
          />
          <KpiCard
            label="Cobertura seccional"
            value={dashboard.cobertura.pct_global ?? 0}
            format={dashboard.cobertura.pct_global != null ? pctFmt : undefined}
            context={coberturaContext}
            icon={<MapIcon />}
            tone="teal"
            delay={240}
          />
        </div>
      </div>

      {/* Tendencia + top secciones */}
      <div className="space-y-4 print:space-y-2">
        <SectionHeading eyebrow="Detalle" title="Tendencia y secciones" />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[360px_1fr] print:grid-cols-2 print:gap-3">
          <ChartFrame
            title="Top secciones"
            caption="Promovidos acumulados"
            empty={porSeccionTop.length === 0}
            className="print:bg-white print:text-black print:border print:border-black/20"
          >
            <Bars
              items={porSeccionTop.map((s) => ({
                label: s.seccion,
                value: s.promovidos,
              }))}
              highlightFirst
            />
          </ChartFrame>

          <ChartFrame
            title="Promovidos por semana"
            caption="Tendencia de captura"
            empty={tendencia.length === 0}
            className="print:bg-white print:text-black print:border print:border-black/20"
          >
            <AreaTrend
              points={tendencia.map((p) => ({
                x: p.semana,
                y: p.promovidos,
              }))}
            />
          </ChartFrame>
        </div>
      </div>

      {/* Casos por estado + alertas de cobertura */}
      <div className="space-y-4 print:space-y-2">
        <SectionHeading
          eyebrow="Detalle"
          title="Atención ciudadana y cobertura"
          note={`${casosPorEstado.length} estados · ${alertas.length} alertas`}
        />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 print:grid-cols-2 print:gap-3">
          <ChartFrame
            title="Casos por estado"
            empty={casosPorEstado.length === 0}
            className="print:bg-white print:text-black print:border print:border-black/20"
          >
            <Bars
              items={casosPorEstado.map((c) => ({
                label: c.estado,
                value: c.n,
              }))}
              highlightFirst
            />
          </ChartFrame>

          <ChartFrame
            title="Secciones en riesgo"
            caption="Faltan promovidos"
            empty={alertas.length === 0}
            className="print:bg-white print:text-black print:border print:border-black/20"
          >
            <Bars
              items={alertas.map((a) => ({
                label: a.seccion,
                value: a.faltan,
              }))}
            />
          </ChartFrame>
        </div>
      </div>

      {/* Alerts (only if present) */}
      {alertas.length > 0 && (
        <Card
          title="Alertas"
          accentDot
          className="reveal print:border print:border-black/20 print:bg-white print:text-black"
        >
          <ul className="space-y-2">
            {alertas.map((a, i) => (
              <li
                key={`${a.seccion}-${i}`}
                className="rounded-card border border-state-warning/40 px-3 py-2 text-sm text-state-warning print:border-black/30 print:text-black"
              >
                <span className="font-semibold">Sección {a.seccion}</span>
                <span className="ml-2 text-ink-muted print:text-black/70">
                  faltan {intFmt.format(a.faltan)} promovidos
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Provenance footer */}
      <div className="card-premium hud-corners reveal flex flex-col gap-2 px-5 py-4 text-xs text-ink-faint sm:flex-row sm:items-center sm:justify-between print:border print:border-black/20 print:bg-white print:text-black/70">
        <span>
          Generado:{" "}
          <span className="font-mono text-ink-muted print:text-black">
            {formatTimestamp(now)}
          </span>
        </span>
        <span className="font-mono uppercase tracking-wide">
          Generado por Atenea
        </span>
      </div>
    </div>
  );
}

interface KpiCardProps {
  label: string;
  value: number;
  context?: string;
  icon: ReactNode;
  tone: "accent" | "teal" | "warm" | "critical";
  delay: number;
  format?: (n: number) => string;
}

function KpiCard({ label, value, context, icon, tone, delay, format }: KpiCardProps) {
  return (
    <MetricCard
      label={label}
      value={format ? format(value) : intFmt.format(value)}
      countTo={value}
      format={format ?? ((n) => intFmt.format(Math.round(n)))}
      context={context}
      icon={icon}
      tone={tone}
      delay={delay}
      className="print:bg-white print:text-black"
    />
  );
}
